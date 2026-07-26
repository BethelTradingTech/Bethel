from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin
from api.database import get_db
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding.service import (
    get_or_create_onboarding,
    get_subscriber,
    recompute_activation,
    refresh_broker_status,
    serialize_onboarding,
)


router = APIRouter(prefix="/onboarding", tags=["Client Onboarding"])


class PlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    billing_interval: Literal["MONTHLY", "QUARTERLY", "ANNUAL"] = "MONTHLY"
    allocation_percent: float = Field(default=100.0, gt=0, le=100)


class PlanSelection(BaseModel):
    plan_id: int


class KycReview(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=500)


class PaymentConfirmation(BaseModel):
    reference: str = Field(min_length=3, max_length=150)


class ApprovalDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=500)


def _plan_dict(plan: SubscriptionPlan):
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "price": plan.price,
        "currency": plan.currency,
        "billing_interval": plan.billing_interval,
        "allocation_percent": plan.allocation_percent,
        "active": plan.active,
    }


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.active.is_(True))
        .order_by(SubscriptionPlan.price)
        .all()
    )
    return [_plan_dict(plan) for plan in plans]


@router.post("/plans", status_code=201)
def create_plan(
    data: PlanCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    existing = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.name == data.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Plan name already exists")

    plan = SubscriptionPlan(
        name=data.name,
        description=data.description,
        price=data.price,
        currency=data.currency.upper(),
        billing_interval=data.billing_interval,
        allocation_percent=data.allocation_percent,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_dict(plan)


@router.get("/{subscriber_id}")
def get_status(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    onboarding = get_or_create_onboarding(db, subscriber_id)
    result = serialize_onboarding(db, onboarding)
    db.commit()
    return result


@router.post("/{subscriber_id}/subscription")
def select_subscription(
    subscriber_id: int,
    data: PlanSelection,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id == data.plan_id,
            SubscriptionPlan.active.is_(True),
        )
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    subscriber = get_subscriber(db, subscriber_id)
    onboarding = get_or_create_onboarding(db, subscriber_id)
    onboarding.plan_id = plan.id
    onboarding.subscription_status = "PENDING_PAYMENT"
    onboarding.payment_status = "UNPAID"
    onboarding.payment_reference = None
    onboarding.admin_approval = "PENDING"
    subscriber.allocation_percent = plan.allocation_percent
    recompute_activation(db, onboarding)
    db.commit()
    return serialize_onboarding(db, onboarding)


@router.post("/{subscriber_id}/kyc/submit")
def submit_kyc(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    onboarding = get_or_create_onboarding(db, subscriber_id)
    onboarding.kyc_status = "PENDING"
    onboarding.kyc_submitted_at = datetime.utcnow()
    onboarding.rejection_reason = None
    onboarding.admin_approval = "PENDING"
    recompute_activation(db, onboarding)
    db.commit()
    return serialize_onboarding(db, onboarding)


@router.post("/{subscriber_id}/kyc/review")
def review_kyc(
    subscriber_id: int,
    data: KycReview,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    onboarding = get_or_create_onboarding(db, subscriber_id)
    if onboarding.kyc_status != "PENDING":
        raise HTTPException(status_code=409, detail="KYC is not pending review")
    onboarding.kyc_status = data.decision
    onboarding.kyc_reviewed_at = datetime.utcnow()
    onboarding.rejection_reason = (
        data.reason if data.decision == "REJECTED" else None
    )
    recompute_activation(db, onboarding)
    db.commit()
    return serialize_onboarding(db, onboarding)


@router.post("/{subscriber_id}/payment/confirm")
def confirm_payment(
    subscriber_id: int,
    data: PaymentConfirmation,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    onboarding = get_or_create_onboarding(db, subscriber_id)
    if onboarding.plan_id is None:
        raise HTTPException(
            status_code=409,
            detail="Select a subscription plan before confirming payment",
        )
    onboarding.payment_status = "PAID"
    onboarding.subscription_status = "ACTIVE"
    onboarding.payment_reference = data.reference
    onboarding.payment_confirmed_at = datetime.utcnow()
    subscriber = get_subscriber(db, subscriber_id)
    subscriber.payment_status = "PAID"
    recompute_activation(db, onboarding)
    db.commit()
    return serialize_onboarding(db, onboarding)


@router.post("/{subscriber_id}/broker/refresh")
def confirm_broker(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    onboarding = get_or_create_onboarding(db, subscriber_id)
    refresh_broker_status(db, onboarding)
    recompute_activation(db, onboarding)
    db.commit()
    return serialize_onboarding(db, onboarding)


@router.post("/{subscriber_id}/approval")
def decide_approval(
    subscriber_id: int,
    data: ApprovalDecision,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    onboarding = get_or_create_onboarding(db, subscriber_id)
    if data.decision == "APPROVED":
        refresh_broker_status(db, onboarding)
        missing = []
        if onboarding.subscription_status != "ACTIVE":
            missing.append("subscription")
        if onboarding.kyc_status != "APPROVED":
            missing.append("kyc")
        if onboarding.payment_status != "PAID":
            missing.append("payment")
        if onboarding.broker_status != "CONNECTED":
            missing.append("broker")
        if missing:
            raise HTTPException(
                status_code=409,
                detail={"message": "Onboarding requirements incomplete", "missing": missing},
            )

    onboarding.admin_approval = data.decision
    onboarding.approved_at = (
        datetime.utcnow() if data.decision == "APPROVED" else None
    )
    onboarding.rejection_reason = (
        data.reason if data.decision == "REJECTED" else None
    )
    recompute_activation(db, onboarding)
    db.commit()
    return serialize_onboarding(db, onboarding)
