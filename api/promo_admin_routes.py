from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin
from api.database import get_db
from api.onboarding.models import SubscriptionPlan
from api.payment_admin.models import PromoCode


router = APIRouter(prefix="/admin/pricing/promos", tags=["Admin Pricing Promotions"])

PromoScope = Literal["ANY_SUBSCRIPTION", "ACTIVATION_FEE", "PLAN"]


class PromoCreate(BaseModel):
    code: str = Field(min_length=3, max_length=40)
    description: str | None = Field(default=None, max_length=255)
    discount_type: Literal["FIXED", "PERCENT"] = "FIXED"
    discount_value: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    scope: PromoScope = "ANY_SUBSCRIPTION"
    target_plan_id: int | None = Field(default=None, ge=1)
    restricted_email: EmailStr | None = None
    max_uses: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    active: bool = True


class PromoUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=255)
    discount_type: Literal["FIXED", "PERCENT"] | None = None
    discount_value: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    scope: PromoScope | None = None
    target_plan_id: int | None = Field(default=None, ge=1)
    restricted_email: EmailStr | None = None
    max_uses: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    active: bool | None = None


def _normalize_code(value: str) -> str:
    import re
    code = re.sub(r"[^A-Z0-9_-]", "", value.strip().upper())
    if len(code) < 3:
        raise HTTPException(status_code=422, detail="Promo code must contain at least 3 letters or numbers")
    return code


def _scope_label(row: PromoCode, db: Session) -> str:
    if row.scope == "ACTIVATION_FEE":
        return "Activation Fee"
    if row.scope == "PLAN" and row.target_plan_id:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == row.target_plan_id).first()
        return plan.name if plan else f"Plan #{row.target_plan_id}"
    return "Any Subscription Plan"


def _validate_scope(db: Session, scope: str, target_plan_id: int | None) -> int | None:
    if scope == "PLAN":
        if not target_plan_id:
            raise HTTPException(status_code=422, detail="Select a subscription plan for this promo code")
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == target_plan_id).first()
        if plan is None or plan.name == "Activation Fee":
            raise HTTPException(status_code=422, detail="Selected subscription plan is invalid")
        return plan.id
    return None


def _promo_dict(row: PromoCode, db: Session):
    return {
        "id": row.id,
        "code": row.code,
        "description": row.description,
        "discount_type": row.discount_type,
        "discount_value": row.discount_value,
        "currency": row.currency,
        "scope": row.scope or "ANY_SUBSCRIPTION",
        "scope_label": _scope_label(row, db),
        "target_plan_id": row.target_plan_id,
        "restricted_email": row.restricted_email,
        "max_uses": row.max_uses,
        "uses_count": row.uses_count,
        "active": row.active,
        "starts_at": row.starts_at.isoformat() + "Z" if row.starts_at else None,
        "expires_at": row.expires_at.isoformat() + "Z" if row.expires_at else None,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() + "Z" if row.created_at else None,
    }


@router.get("")
def list_promos(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    rows = db.query(PromoCode).order_by(PromoCode.id.desc()).all()
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.active.is_(True)).order_by(SubscriptionPlan.price).all()
    return {
        "status": "success",
        "promos": [_promo_dict(row, db) for row in rows],
        "targets": [
            {"scope": "ANY_SUBSCRIPTION", "label": "Any Subscription Plan", "plan_id": None},
            {"scope": "ACTIVATION_FEE", "label": "Activation Fee", "plan_id": None},
            *[
                {"scope": "PLAN", "label": plan.name, "plan_id": plan.id}
                for plan in plans
                if plan.name != "Activation Fee"
            ],
        ],
    }


@router.post("", status_code=201)
def create_promo(data: PromoCreate, db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    code = _normalize_code(data.code)
    if data.discount_type == "PERCENT" and data.discount_value > 100:
        raise HTTPException(status_code=422, detail="Percentage discount cannot exceed 100")
    if data.starts_at and data.expires_at and data.expires_at <= data.starts_at:
        raise HTTPException(status_code=422, detail="Expiry must be after the start date")
    target_plan_id = _validate_scope(db, data.scope, data.target_plan_id)
    row = PromoCode(
        code=code,
        description=data.description,
        discount_type=data.discount_type,
        discount_value=float(data.discount_value),
        currency=data.currency.upper(),
        scope=data.scope,
        target_plan_id=target_plan_id,
        restricted_email=str(data.restricted_email).lower() if data.restricted_email else None,
        max_uses=data.max_uses,
        active=data.active,
        starts_at=data.starts_at,
        expires_at=data.expires_at,
        created_by=str(admin.get("email") or admin.get("sub") or "admin"),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Promo code already exists") from exc
    db.refresh(row)
    return _promo_dict(row, db)


@router.patch("/{promo_id}")
def update_promo(promo_id: int, data: PromoUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    row = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Promo code not found")
    values = data.model_dump(exclude_unset=True)
    discount_type = values.get("discount_type", row.discount_type)
    discount_value = values.get("discount_value", row.discount_value)
    if discount_type == "PERCENT" and discount_value > 100:
        raise HTTPException(status_code=422, detail="Percentage discount cannot exceed 100")
    scope = values.get("scope", row.scope or "ANY_SUBSCRIPTION")
    target = values.get("target_plan_id", row.target_plan_id)
    values["target_plan_id"] = _validate_scope(db, scope, target)
    values["scope"] = scope
    for key, value in values.items():
        if key == "currency" and value:
            value = value.upper()
        if key == "restricted_email" and value:
            value = str(value).lower()
        setattr(row, key, value)
    if row.starts_at and row.expires_at and row.expires_at <= row.starts_at:
        raise HTTPException(status_code=422, detail="Expiry must be after the start date")
    db.commit()
    db.refresh(row)
    return _promo_dict(row, db)
