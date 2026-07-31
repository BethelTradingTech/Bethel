import calendar
import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from api.copytrading.models import CopySubscriber
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.subscription_lifecycle.models import SubscriptionAudit, SubscriptionLifecycle


GRACE_DAYS = max(0, int(os.getenv("SUBSCRIPTION_GRACE_DAYS", "7")))


def add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def period_end(start: datetime, interval: str) -> datetime:
    interval = (interval or "MONTHLY").upper()
    if interval == "DAILY":
        return start + timedelta(days=1)
    if interval == "WEEKLY":
        return start + timedelta(days=7)
    if interval == "YEARLY":
        return add_months(start, 12)
    return add_months(start, 1)


def add_audit(
    db: Session,
    lifecycle: SubscriptionLifecycle,
    action: str,
    previous_status: str | None,
    new_status: str,
    administrator: str | None = None,
):
    db.add(SubscriptionAudit(
        subscriber_id=lifecycle.subscriber_id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        reference=lifecycle.last_payment_reference,
        administrator=administrator,
    ))


def start_or_renew(
    db: Session,
    onboarding: ClientOnboarding,
    *,
    administrator: str | None = None,
    force: bool = False,
):
    if onboarding.plan_id is None:
        return None
    plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.id == onboarding.plan_id)
        .first()
    )
    if plan is None:
        return None
    reference = onboarding.payment_reference
    lifecycle = (
        db.query(SubscriptionLifecycle)
        .filter(SubscriptionLifecycle.subscriber_id == onboarding.subscriber_id)
        .first()
    )
    if (
        lifecycle is not None
        and not force
        and lifecycle.last_payment_reference == reference
    ):
        return lifecycle

    now = onboarding.payment_confirmed_at or datetime.utcnow()
    if lifecycle is None:
        lifecycle = SubscriptionLifecycle(
            subscriber_id=onboarding.subscriber_id,
            plan_id=plan.id,
            current_period_start=now,
            current_period_end=period_end(now, plan.billing_interval),
            grace_until=period_end(now, plan.billing_interval) + timedelta(days=GRACE_DAYS),
            last_payment_reference=reference,
            status="ACTIVE",
        )
        db.add(lifecycle)
        db.flush()
        add_audit(db, lifecycle, "START", None, "ACTIVE", administrator)
    else:
        previous = lifecycle.status
        start = max(datetime.utcnow(), lifecycle.current_period_end)
        lifecycle.plan_id = plan.id
        lifecycle.current_period_start = start
        lifecycle.current_period_end = period_end(start, plan.billing_interval)
        lifecycle.grace_until = lifecycle.current_period_end + timedelta(days=GRACE_DAYS)
        lifecycle.last_payment_reference = reference
        lifecycle.manual_suspended = False
        lifecycle.suspended_at = None
        lifecycle.status = "ACTIVE"
        add_audit(db, lifecycle, "RENEW", previous, "ACTIVE", administrator)
    return lifecycle


def enforce_subscription_state(db: Session, onboarding: ClientOnboarding):
    lifecycle = (
        db.query(SubscriptionLifecycle)
        .filter(SubscriptionLifecycle.subscriber_id == onboarding.subscriber_id)
        .first()
    )
    if (
        onboarding.payment_status == "PAID"
        and onboarding.plan_id is not None
        and (
            lifecycle is None
            or lifecycle.last_payment_reference != onboarding.payment_reference
        )
    ):
        lifecycle = start_or_renew(db, onboarding)
    if lifecycle is None:
        return None

    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == onboarding.subscriber_id)
        .first()
    )
    now = datetime.utcnow()
    previous = lifecycle.status
    if lifecycle.manual_suspended:
        lifecycle.status = "SUSPENDED"
        onboarding.subscription_status = "SUSPENDED"
        onboarding.copy_trading_status = "INACTIVE"
        if subscriber:
            subscriber.status = "SUSPENDED"
    elif now <= lifecycle.current_period_end:
        lifecycle.status = "ACTIVE"
        onboarding.subscription_status = "ACTIVE"
    elif now <= lifecycle.grace_until:
        lifecycle.status = "GRACE"
        onboarding.subscription_status = "GRACE"
    else:
        lifecycle.status = "EXPIRED"
        onboarding.subscription_status = "EXPIRED"
        onboarding.copy_trading_status = "INACTIVE"
        if subscriber:
            subscriber.status = "SUSPENDED"
    if lifecycle.status != previous:
        add_audit(db, lifecycle, "STATE_CHANGE", previous, lifecycle.status)
    return lifecycle


def lifecycle_snapshot(db: Session, subscriber_id: int):
    lifecycle = (
        db.query(SubscriptionLifecycle)
        .filter(SubscriptionLifecycle.subscriber_id == subscriber_id)
        .first()
    )
    if lifecycle is None:
        return None
    now = datetime.utcnow()
    days_remaining = max(
        0,
        (lifecycle.current_period_end.date() - now.date()).days,
    )
    return {
        "status": lifecycle.status,
        "current_period_start": lifecycle.current_period_start.isoformat(),
        "current_period_end": lifecycle.current_period_end.isoformat(),
        "grace_until": lifecycle.grace_until.isoformat(),
        "days_remaining": days_remaining,
        "renewal_due": lifecycle.status in ("GRACE", "EXPIRED"),
        "manual_suspended": lifecycle.manual_suspended,
    }


def subscriber_can_copy(db: Session, subscriber_id: int) -> bool:
    from api.legal.service import all_current_accepted
    from api.profit_share.service import profit_share_accepted

    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding is None:
        return False
    lifecycle = enforce_subscription_state(db, onboarding)
    if lifecycle is None:
        return False
    return (
        lifecycle.status in ("ACTIVE", "GRACE")
        and onboarding.kyc_status == "APPROVED"
        and onboarding.payment_status == "PAID"
        and onboarding.broker_status == "CONNECTED"
        and onboarding.admin_approval == "APPROVED"
        and onboarding.copy_trading_status == "ACTIVE"
        and profit_share_accepted(db, subscriber_id)
        and all_current_accepted(db, subscriber_id)
    )


def sweep_subscriptions(db: Session):
    onboardings = db.query(ClientOnboarding).all()
    counts = {"ACTIVE": 0, "GRACE": 0, "EXPIRED": 0, "SUSPENDED": 0, "NONE": 0}
    for onboarding in onboardings:
        lifecycle = enforce_subscription_state(db, onboarding)
        key = lifecycle.status if lifecycle else "NONE"
        counts[key] = counts.get(key, 0) + 1
    db.flush()
    return counts
