import hashlib
import hmac
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin, require_super_admin
from api.broker_accounts.models import BrokerAccount
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding.service import recompute_activation
from api.subscription_lifecycle.models import (
    PromoRedemption,
    SubscriptionAudit,
    SubscriptionLifecycle,
)
from api.subscription_lifecycle.service import (
    enforce_subscription_state,
    lifecycle_snapshot,
    start_or_renew,
    sweep_subscriptions,
)


router = APIRouter(tags=["Subscription Lifecycle"])

OWNER_PROMO_HASH = "3d149428f278eeea00cdd462d5c1532f4341ec6643ff47a339359e6680743e30"
OWNER_PROMO_VALUE_USD = 100.0
OWNER_PROMO_EXPIRES_AT = datetime(2027, 12, 31, 23, 59, 59)


class RenewalRequest(BaseModel):
    reference: str = Field(min_length=4, max_length=150)


class SuspensionRequest(BaseModel):
    suspended: bool


class PromoApplyRequest(BaseModel):
    code: str = Field(min_length=8, max_length=80)




@router.post("/subscriptions/{subscriber_id}/promo/apply")
def apply_owner_promo(
    subscriber_id: int,
    data: PromoApplyRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_super_admin),
):
    """Apply the reusable owner promotion once to each owner-controlled account."""
    supplied_hash = hashlib.sha256(data.code.strip().encode("utf-8")).hexdigest()
    if not hmac.compare_digest(supplied_hash, OWNER_PROMO_HASH):
        raise HTTPException(status_code=404, detail="Promotion code is invalid")
    if datetime.utcnow() > OWNER_PROMO_EXPIRES_AT:
        raise HTTPException(status_code=410, detail="Promotion code has expired")

    admin_identity = str(admin.get("email") or admin.get("sub") or "super_admin").strip().casefold()

    account = db.query(BrokerAccount).filter(
        BrokerAccount.subscriber_id == subscriber_id,
        BrokerAccount.status != "ARCHIVED",
    ).first()
    if account is None:
        raise HTTPException(
            status_code=403,
            detail="Link and verify the owner-controlled follower account first",
        )

    redemption_hash = hashlib.sha256(
        f"{OWNER_PROMO_HASH}:{subscriber_id}".encode("utf-8")
    ).hexdigest()
    existing = db.query(PromoRedemption).filter(
        PromoRedemption.code_hash == redemption_hash
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Owner promotion has already been used for this subscriber account",
        )

    onboarding = db.query(ClientOnboarding).filter(
        ClientOnboarding.subscriber_id == subscriber_id
    ).first()
    if onboarding is None or onboarding.plan_id is None:
        raise HTTPException(status_code=404, detail="Select a subscription plan first")

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == onboarding.plan_id
    ).first()
    if plan is None or plan.currency.upper() != "USD":
        raise HTTPException(status_code=409, detail="A USD subscription plan is required")
    if abs(float(plan.price) - OWNER_PROMO_VALUE_USD) > 0.001:
        raise HTTPException(
            status_code=409,
            detail="Owner promotion applies only to the 100 USD subscription",
        )

    reference = f"PROMO-OWNER100-{subscriber_id}-{int(datetime.utcnow().timestamp())}"
    onboarding.payment_status = "PAID"
    onboarding.payment_reference = reference
    onboarding.payment_confirmed_at = datetime.utcnow()
    db.add(PromoRedemption(
        code_hash=redemption_hash,
        subscriber_id=subscriber_id,
        broker_login=account.login,
        original_amount_usd=float(plan.price),
        discount_amount_usd=OWNER_PROMO_VALUE_USD,
        final_amount_usd=0.0,
        payment_reference=reference,
    ))
    lifecycle = start_or_renew(
        db,
        onboarding,
        administrator=f"OWNER_PROMO:{admin_identity}",
        force=False,
    )
    if lifecycle is None:
        raise HTTPException(status_code=409, detail="Unable to activate subscription")
    recompute_activation(db, onboarding)
    db.commit()
    return {
        "status": "success",
        "subscriber_id": subscriber_id,
        "broker_login": account.login,
        "promotion": "OWNER100",
        "original_amount_usd": float(plan.price),
        "discount_amount_usd": OWNER_PROMO_VALUE_USD,
        "amount_due_usd": 0.0,
        "payment_reference": reference,
        "subscription": lifecycle_snapshot(db, subscriber_id),
    }


@router.get("/subscriptions/{subscriber_id}")
def subscription_status(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding is None:
        raise HTTPException(status_code=404, detail="Onboarding record not found")
    enforce_subscription_state(db, onboarding)
    db.commit()
    return {
        "subscriber_id": subscriber_id,
        "subscription": lifecycle_snapshot(db, subscriber_id),
    }


@router.get("/admin/subscriptions")
def admin_subscriptions(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    counts = sweep_subscriptions(db)
    db.commit()
    subscribers = {
        row.id: row
        for row in db.query(CopySubscriber).all()
    }
    rows = (
        db.query(SubscriptionLifecycle)
        .order_by(SubscriptionLifecycle.current_period_end.asc())
        .all()
    )
    return {
        "status": "success",
        "counts": counts,
        "subscriptions": [
            {
                "subscriber_id": row.subscriber_id,
                "subscriber_name": getattr(subscribers.get(row.subscriber_id), "name", None),
                "subscriber_email": getattr(subscribers.get(row.subscriber_id), "email", None),
                "plan_id": row.plan_id,
                **lifecycle_snapshot(db, row.subscriber_id),
            }
            for row in rows
        ],
    }


@router.post("/admin/subscriptions/sweep")
def sweep_now(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    counts = sweep_subscriptions(db)
    db.commit()
    return {"status": "success", "counts": counts}


@router.post("/admin/subscriptions/{subscriber_id}/renew")
def admin_renew(
    subscriber_id: int,
    data: RenewalRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding is None or onboarding.plan_id is None:
        raise HTTPException(status_code=404, detail="Subscription selection not found")
    onboarding.payment_status = "PAID"
    onboarding.payment_reference = data.reference
    onboarding.payment_confirmed_at = datetime.utcnow()
    lifecycle = start_or_renew(
        db,
        onboarding,
        administrator=str(admin.get("email") or admin.get("sub") or "admin"),
        force=True,
    )
    if lifecycle is None:
        raise HTTPException(status_code=409, detail="Unable to renew subscription")
    recompute_activation(db, onboarding)
    db.commit()
    return {"status": "success", "subscription": lifecycle_snapshot(db, subscriber_id)}


@router.post("/admin/subscriptions/{subscriber_id}/suspension")
def admin_suspension(
    subscriber_id: int,
    data: SuspensionRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    lifecycle = (
        db.query(SubscriptionLifecycle)
        .filter(SubscriptionLifecycle.subscriber_id == subscriber_id)
        .first()
    )
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if lifecycle is None or onboarding is None:
        raise HTTPException(status_code=404, detail="Subscription lifecycle not found")
    previous = lifecycle.status
    lifecycle.manual_suspended = data.suspended
    lifecycle.suspended_at = datetime.utcnow() if data.suspended else None
    enforce_subscription_state(db, onboarding)
    db.add(SubscriptionAudit(
        subscriber_id=subscriber_id,
        action="ADMIN_SUSPEND" if data.suspended else "ADMIN_RESUME",
        previous_status=previous,
        new_status=lifecycle.status,
        reference=lifecycle.last_payment_reference,
        administrator=str(admin.get("email") or admin.get("sub") or "admin"),
    ))
    recompute_activation(db, onboarding)
    db.commit()
    return {"status": "success", "subscription": lifecycle_snapshot(db, subscriber_id)}


@router.get("/admin/subscriptions/reminders")
def renewal_reminders(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    sweep_subscriptions(db)
    db.commit()
    rows = db.query(SubscriptionLifecycle).all()
    reminders = []
    for row in rows:
        snapshot = lifecycle_snapshot(db, row.subscriber_id)
        if row.status in ("GRACE", "EXPIRED") or snapshot["days_remaining"] in (1, 3, 7):
            reminders.append({"subscriber_id": row.subscriber_id, **snapshot})
    return {"status": "success", "reminders": reminders}
