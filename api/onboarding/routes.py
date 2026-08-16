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

ACTIVATION_FEE_NAME = "Activation Fee"
LAUNCH_PLANS = (
    {"name": "Starter", "description": "Entry subscription for individual Bethel accounts.", "price": 49.0, "billing_interval": "MONTHLY"},
    {"name": "Standard", "description": "Standard Bethel subscription for active individual accounts.", "price": 99.0, "billing_interval": "MONTHLY"},
    {"name": "Professional", "description": "Advanced Bethel subscription with expanded service access.", "price": 199.0, "billing_interval": "MONTHLY"},
    {"name": "Enterprise", "description": "Custom commercial plan. Contact Bethel for enterprise pricing.", "price": 0.0, "billing_interval": "MONTHLY"},
    {"name": ACTIVATION_FEE_NAME, "description": "One-time Bethel account activation fee.", "price": 100.0, "billing_interval": "ONE_TIME"},
)


def _sync_launch_plans(db: Session):
    """Seed missing commercial items without overwriting admin-managed prices."""
    changed = False
    for item in LAUNCH_PLANS:
        plan = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.name == item["name"])
            .first()
        )
        if plan is None:
            plan = SubscriptionPlan(
                name=item["name"],
                description=item["description"],
                price=item["price"],
                currency="USD",
                billing_interval=item["billing_interval"],
                allocation_percent=100.0,
                active=True,
            )
            db.add(plan)
            changed = True
    if changed:
        db.commit()


def _activation_fee(db: Session) -> float:
    _sync_launch_plans(db)
    row = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.name == ACTIVATION_FEE_NAME)
        .first()
    )
    return round(float(row.price), 2) if row and row.active else 0.0


class PlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    billing_interval: Literal["ONE_TIME", "MONTHLY", "QUARTERLY", "ANNUAL"] = "MONTHLY"
    allocation_percent: float = Field(default=100.0, gt=0, le=100)
    active: bool = True


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    billing_interval: Literal["ONE_TIME", "MONTHLY", "QUARTERLY", "ANNUAL"] | None = None
    allocation_percent: float | None = Field(default=None, gt=0, le=100)
    active: bool | None = None


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


def _plan_dict(plan: SubscriptionPlan, activation_fee_usd: float | None = None):
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "price": plan.price,
        "currency": plan.currency,
        "billing_interval": plan.billing_interval,
        "allocation_percent": plan.allocation_percent,
        "active": plan.active,
        "activation_fee_usd": activation_fee_usd,
        "checkout_available": float(plan.price) > 0,
    }


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    _sync_launch_plans(db)
    activation_fee = _activation_fee(db)
    launch_names = [item["name"] for item in LAUNCH_PLANS if item["name"] != ACTIVATION_FEE_NAME]
    plans = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.active.is_(True),
            SubscriptionPlan.name.in_(launch_names),
        )
        .order_by(
            SubscriptionPlan.price == 0,
            SubscriptionPlan.price,
        )
        .all()
    )
    return [_plan_dict(plan, activation_fee) for plan in plans]


@router.get("/plans/admin")
def list_plans_admin(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    _sync_launch_plans(db)
    rows = db.query(SubscriptionPlan).order_by(SubscriptionPlan.id.asc()).all()
    return {"status": "success", "plans": [_plan_dict(row) for row in rows]}


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
        active=data.active,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_dict(plan)


@router.patch("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    values = data.model_dump(exclude_unset=True)
    if "name" in values and values["name"] != plan.name:
        duplicate = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == values["name"]).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Pricing item name already exists")
    for key, value in values.items():
        if key == "currency" and value:
            value = value.upper()
        setattr(plan, key, value)
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
    if plan is None or plan.name == ACTIVATION_FEE_NAME:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    if float(plan.price) <= 0:
        raise HTTPException(
            status_code=409,
            detail="Enterprise pricing requires a custom commercial agreement",
        )

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
    onboarding.payment_status = "PAID"
    onboarding.subscription_status = "ACTIVE"
    onboarding.payment_reference = data.reference
    onboarding.payment_confirmed_at = datetime.utcnow()
    recompute_activation(db, onboarding)
    db.commit()
    return serialize_onboarding(db, onboarding)


@router.post("/{subscriber_id}/approval")
def approve_subscriber(
    subscriber_id: int,
    data: ApprovalDecision,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    onboarding = get_or_create_onboarding(db, subscriber_id)
    onboarding.admin_approval = data.decision
    onboarding.approved_at = datetime.utcnow() if data.decision == "APPROVED" else None
    onboarding.rejection_reason = data.reason if data.decision == "REJECTED" else None
    recompute_activation(db, onboarding)
    db.commit()
    return serialize_onboarding(db, onboarding)
