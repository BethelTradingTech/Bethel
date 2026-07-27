from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding
from api.onboarding.service import recompute_activation
from api.subscription_lifecycle.models import SubscriptionAudit, SubscriptionLifecycle
from api.subscription_lifecycle.service import (
    enforce_subscription_state,
    lifecycle_snapshot,
    start_or_renew,
    sweep_subscriptions,
)


router = APIRouter(tags=["Subscription Lifecycle"])


class RenewalRequest(BaseModel):
    reference: str = Field(min_length=4, max_length=150)


class SuspensionRequest(BaseModel):
    suspended: bool


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
