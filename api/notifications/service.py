from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from api.copytrading.models import CopySubscriber
from api.notifications.emailer import record_and_send
from api.notifications.models import NotificationState
from api.onboarding.models import ClientOnboarding
from api.subscription_lifecycle.models import SubscriptionLifecycle


def status_message(label: str, value: str, subscriber_name: str) -> tuple[str, str]:
    subject = f"Bethel Trading Technologies: {label} update"
    body = (
        f"Hello {subscriber_name},\n\n"
        f"Your {label.lower()} status is now: {value}.\n\n"
        "Sign in to the Bethel subscriber portal for details.\n\n"
        "Bethel Trading Technologies"
    )
    return subject, body


def synchronize_status_notifications(db: Session) -> dict:
    queued = 0
    subscribers = {row.id: row for row in db.query(CopySubscriber).all()}
    onboardings = db.query(ClientOnboarding).all()
    for onboarding in onboardings:
        subscriber = subscribers.get(onboarding.subscriber_id)
        if not subscriber or not subscriber.email:
            continue
        state = (
            db.query(NotificationState)
            .filter(NotificationState.subscriber_id == subscriber.id)
            .first()
        )
        current = {
            "kyc_status": onboarding.kyc_status,
            "payment_status": onboarding.payment_status,
            "activation_status": onboarding.copy_trading_status,
            "subscription_status": onboarding.subscription_status,
        }
        if state is None:
            state = NotificationState(subscriber_id=subscriber.id, **current)
            db.add(state)
            continue
        labels = {
            "kyc_status": "KYC",
            "payment_status": "Payment",
            "activation_status": "Account activation",
            "subscription_status": "Subscription",
        }
        for field, value in current.items():
            previous = getattr(state, field)
            if previous == value:
                continue
            subject, body = status_message(labels[field], value, subscriber.name)
            key = f"status:{subscriber.id}:{field}:{previous}:{value}"
            record_and_send(
                db,
                recipient=subscriber.email,
                subscriber_id=subscriber.id,
                message_type=field.upper(),
                subject=subject,
                text_body=body,
                deduplication_key=key,
            )
            setattr(state, field, value)
            queued += 1
    return {"status_notifications": queued}


def queue_renewal_reminders(db: Session, days: int = 7) -> dict:
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days)
    subscribers = {row.id: row for row in db.query(CopySubscriber).all()}
    rows = (
        db.query(SubscriptionLifecycle)
        .filter(
            SubscriptionLifecycle.current_period_end >= now,
            SubscriptionLifecycle.current_period_end <= cutoff,
            SubscriptionLifecycle.status.in_(("ACTIVE", "GRACE")),
        )
        .all()
    )
    queued = 0
    for lifecycle in rows:
        subscriber = subscribers.get(lifecycle.subscriber_id)
        if not subscriber or not subscriber.email:
            continue
        end = lifecycle.current_period_end
        key = f"renewal:{subscriber.id}:{end.date().isoformat()}"
        delivery = record_and_send(
            db,
            recipient=subscriber.email,
            subscriber_id=subscriber.id,
            message_type="SUBSCRIPTION_RENEWAL",
            subject="Bethel subscription renewal reminder",
            text_body=(
                f"Hello {subscriber.name},\n\n"
                f"Your subscription period ends on {end.date().isoformat()}. "
                "Please renew through the subscriber portal to avoid interruption.\n\n"
                "Bethel Trading Technologies"
            ),
            deduplication_key=key,
        )
        if delivery.created_at >= now:
            queued += 1
    return {"renewal_reminders": queued}
