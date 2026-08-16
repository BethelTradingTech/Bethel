import json
import re
import secrets
import time
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding.service import get_or_create_onboarding, recompute_activation
from api.payment_admin.models import PromoCode, PromoRedemption
from api.payments.binance_client import signed_post, verify_webhook
from api.payments.models import BinancePayment


router = APIRouter(prefix="/payments/binance", tags=["Binance Pay USDT"])
promo_router = APIRouter(prefix="/payments/promos", tags=["Promotion Codes"])
PromoScope = Literal["ANY_SUBSCRIPTION", "ACTIVATION_FEE", "PLAN"]
ACTIVATION_FEE_NAME = "Activation Fee"


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


class PromoQuote(BaseModel):
    code: str = Field(min_length=3, max_length=40)


def _normalize_code(value: str) -> str:
    code = re.sub(r"[^A-Z0-9_-]", "", value.strip().upper())
    if len(code) < 3:
        raise HTTPException(status_code=422, detail="Promo code must contain at least 3 letters or numbers")
    return code


def _promo_targets(db: Session):
    plans = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.active.is_(True))
        .order_by(SubscriptionPlan.price.asc(), SubscriptionPlan.name.asc())
        .all()
    )
    return [
        {"scope": "ACTIVATION_FEE", "label": "Activation Fee", "plan_id": None},
        {"scope": "ANY_SUBSCRIPTION", "label": "Any Subscription Plan", "plan_id": None},
        *[
            {"scope": "PLAN", "label": plan.name, "plan_id": plan.id}
            for plan in plans
            if plan.name != ACTIVATION_FEE_NAME
        ],
    ]


def _validate_scope(db: Session, scope: str, target_plan_id: int | None) -> int | None:
    if scope == "PLAN":
        if not target_plan_id:
            raise HTTPException(status_code=422, detail="Select a subscription plan for this promo code")
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == target_plan_id).first()
        if plan is None or plan.name == ACTIVATION_FEE_NAME:
            raise HTTPException(status_code=422, detail="Selected subscription plan is invalid")
        return plan.id
    return None


def _scope_label(row: PromoCode, db: Session) -> str:
    scope = row.scope or "ANY_SUBSCRIPTION"
    if scope == "ACTIVATION_FEE":
        return "Activation Fee"
    if scope == "PLAN" and row.target_plan_id:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == row.target_plan_id).first()
        return plan.name if plan else f"Plan #{row.target_plan_id}"
    return "Any Subscription Plan"


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


def _validate_promo(db: Session, subscriber_id: int, code: str):
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == subscriber_id).first()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    onboarding = get_or_create_onboarding(db, subscriber_id)
    if onboarding.plan_id is None:
        raise HTTPException(status_code=409, detail="Select a subscription plan first")
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == onboarding.plan_id).first()
    if plan is None or not plan.active:
        raise HTTPException(status_code=409, detail="Subscription plan is unavailable")
    promo = db.query(PromoCode).filter(func.upper(PromoCode.code) == _normalize_code(code)).first()
    if promo is None:
        raise HTTPException(status_code=404, detail="Promo code is invalid")
    now = datetime.utcnow()
    if not promo.active:
        raise HTTPException(status_code=409, detail="Promo code is inactive")
    if promo.starts_at and promo.starts_at > now:
        raise HTTPException(status_code=409, detail="Promo code is not active yet")
    if promo.expires_at and promo.expires_at <= now:
        raise HTTPException(status_code=409, detail="Promo code has expired")
    if promo.max_uses is not None and promo.uses_count >= promo.max_uses:
        raise HTTPException(status_code=409, detail="Promo code usage limit has been reached")
    if promo.restricted_email and promo.restricted_email.lower() != subscriber.email.lower():
        raise HTTPException(status_code=403, detail="Promo code is not assigned to this subscriber")
    scope = promo.scope or "ANY_SUBSCRIPTION"
    if scope == "ACTIVATION_FEE":
        raise HTTPException(status_code=409, detail="This promo applies only to the activation fee")
    if scope == "PLAN" and promo.target_plan_id != plan.id:
        raise HTTPException(status_code=409, detail=f"This promo applies only to {_scope_label(promo, db)}")
    if promo.discount_type == "PERCENT" and promo.discount_value > 100:
        raise HTTPException(status_code=409, detail="Promo percentage is invalid")
    if promo.discount_type == "FIXED" and promo.currency.upper() != plan.currency.upper():
        raise HTTPException(status_code=409, detail="Promo currency does not match the subscription plan")
    original = round(float(plan.price), 2)
    discount = (
        original * float(promo.discount_value) / 100.0
        if promo.discount_type == "PERCENT"
        else float(promo.discount_value)
    )
    discount = round(min(original, max(0.0, discount)), 2)
    return subscriber, onboarding, plan, promo, original, discount, round(original - discount, 2)


@promo_router.get("/admin")
def list_promo_codes(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    rows = db.query(PromoCode).order_by(PromoCode.id.desc()).all()
    return {
        "status": "success",
        "promos": [_promo_dict(row, db) for row in rows],
        "targets": _promo_targets(db),
    }


@promo_router.post("/admin", status_code=201)
def create_promo_code(
    data: PromoCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
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


@promo_router.patch("/admin/{promo_id}")
def update_promo_code(
    promo_id: int,
    data: PromoUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    row = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Promo code not found")
    values = data.model_dump(exclude_unset=True)
    if values.get("discount_type", row.discount_type) == "PERCENT" and values.get("discount_value", row.discount_value) > 100:
        raise HTTPException(status_code=422, detail="Percentage discount cannot exceed 100")
    scope = values.get("scope", row.scope or "ANY_SUBSCRIPTION")
    target_plan_id = values.get("target_plan_id", row.target_plan_id)
    values["scope"] = scope
    values["target_plan_id"] = _validate_scope(db, scope, target_plan_id)
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


@promo_router.post("/{subscriber_id}/quote")
def quote_promo_code(
    subscriber_id: int,
    data: PromoQuote,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    _, _, plan, promo, original, discount, final = _validate_promo(db, subscriber_id, data.code)
    return {
        "status": "valid",
        "promo_code": promo.code,
        "scope": promo.scope or "ANY_SUBSCRIPTION",
        "scope_label": _scope_label(promo, db),
        "plan_id": plan.id,
        "original_amount": original,
        "discount_amount": discount,
        "final_amount": final,
        "currency": plan.currency,
    }


@promo_router.post("/{subscriber_id}/redeem")
def redeem_promo_code(
    subscriber_id: int,
    data: PromoQuote,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    subscriber, onboarding, plan, promo, original, discount, final = _validate_promo(db, subscriber_id, data.code)
    redemption = PromoRedemption(
        promo_code_id=promo.id,
        subscriber_id=subscriber_id,
        plan_id=plan.id,
        original_amount=original,
        discount_amount=discount,
        final_amount=final,
        currency=plan.currency.upper(),
        status="REDEEMED" if final == 0 else "APPLIED",
    )
    db.add(redemption)
    promo.uses_count += 1
    onboarding.payment_reference = f"PROMO:{promo.code}"
    if final == 0:
        onboarding.payment_status = "PAID"
        onboarding.subscription_status = "ACTIVE"
        onboarding.payment_confirmed_at = datetime.utcnow()
        subscriber.payment_status = "PAID"
        recompute_activation(db, onboarding)
    else:
        onboarding.payment_status = "UNPAID"
        onboarding.subscription_status = "PENDING_PAYMENT"
    db.commit()
    return {
        "status": redemption.status,
        "promo_code": promo.code,
        "scope": promo.scope or "ANY_SUBSCRIPTION",
        "scope_label": _scope_label(promo, db),
        "original_amount": original,
        "discount_amount": discount,
        "final_amount": final,
        "currency": plan.currency,
        "payment_waived": final == 0,
    }


@router.post("/{subscriber_id}/order")
def create_binance_order(
    subscriber_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    onboarding = get_or_create_onboarding(db, subscriber_id)
    if onboarding.plan_id is None:
        raise HTTPException(status_code=409, detail="Select a subscription plan first")
    plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.id == onboarding.plan_id)
        .first()
    )
    if plan is None or not plan.active:
        raise HTTPException(status_code=409, detail="Subscription plan is unavailable")

    trade_no = (
        f"BTT{subscriber_id}{int(time.time())}{secrets.randbelow(100000):05d}"
    )[:32]
    public_base = str(request.base_url).rstrip("/")
    payload = {
        "env": {"terminalType": "WEB"},
        "merchantTradeNo": trade_no,
        "fiatAmount": round(float(plan.price), 2),
        "fiatCurrency": str(plan.currency or "USD").upper(),
        "supportPayCurrency": "USDT",
        "description": f"Bethel {plan.name} subscription",
        "goodsDetails": [
            {
                "goodsType": "02",
                "goodsCategory": "Z000",
                "referenceGoodsId": f"PLAN{plan.id}",
                "goodsName": "Bethel Trading Technology Subscription",
                "goodsDetail": str(plan.description or plan.name)[:256],
            }
        ],
        "passThroughInfo": f"subscriber:{subscriber_id}",
        "returnUrl": public_base + "/investor-frontend/onboarding.html?payment=success",
        "cancelUrl": public_base + "/investor-frontend/onboarding.html?payment=cancelled",
        "webhookUrl": public_base + "/payments/binance/webhook",
    }
    data = signed_post("/binancepay/openapi/v3/order", payload)
    payment = BinancePayment(
        subscriber_id=subscriber_id,
        plan_id=plan.id,
        merchant_trade_no=trade_no,
        prepay_id=str(data.get("prepayId") or ""),
        fiat_amount=float(plan.price),
        fiat_currency=str(plan.currency or "USD").upper(),
        payment_currency="USDT",
        status="PENDING",
        checkout_url=data.get("checkoutUrl") or data.get("universalUrl"),
    )
    db.add(payment)
    onboarding.payment_status = "PENDING_VERIFICATION"
    onboarding.payment_reference = trade_no
    onboarding.payment_confirmed_at = None
    onboarding.admin_approval = "PENDING"
    recompute_activation(db, onboarding)
    db.commit()
    return {
        "merchant_trade_no": trade_no,
        "status": payment.status,
        "checkout_url": payment.checkout_url,
        "deeplink": data.get("deeplink"),
        "qr_content": data.get("qrContent"),
        "currency": data.get("currency") or "USDT",
        "amount": data.get("totalFee"),
    }


@router.get("/{subscriber_id}/latest")
def latest_payment(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    payment = (
        db.query(BinancePayment)
        .filter(BinancePayment.subscriber_id == subscriber_id)
        .order_by(BinancePayment.id.desc())
        .first()
    )
    if payment is None:
        return {"status": "not_found"}
    return {
        "merchant_trade_no": payment.merchant_trade_no,
        "status": payment.status,
        "checkout_url": payment.checkout_url,
        "currency": payment.payment_currency,
        "fiat_amount": payment.fiat_amount,
        "fiat_currency": payment.fiat_currency,
        "transaction_id": payment.transaction_id,
    }


@router.post("/webhook")
async def binance_webhook(
    request: Request,
    binancepay_timestamp: str = Header(default=""),
    binancepay_nonce: str = Header(default=""),
    binancepay_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    verify_webhook(
        raw_body,
        binancepay_timestamp,
        binancepay_nonce,
        binancepay_signature,
    )
    try:
        payload = json.loads(raw_body.decode("utf-8"))
        data = json.loads(payload.get("data") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid Binance webhook JSON") from error

    trade_no = str(data.get("merchantTradeNo") or "")
    payment = (
        db.query(BinancePayment)
        .filter(BinancePayment.merchant_trade_no == trade_no)
        .first()
    )
    if payment is None:
        return {"returnCode": "FAIL", "returnMessage": "Order not found"}

    if payload.get("bizStatus") == "PAY_SUCCESS":
        payment.status = "PAID"
        payment.transaction_id = str(data.get("transactionId") or "")
        payment.paid_at = datetime.utcnow()
        onboarding = (
            db.query(ClientOnboarding)
            .filter(ClientOnboarding.subscriber_id == payment.subscriber_id)
            .first()
        )
        if onboarding is not None:
            onboarding.payment_status = "PAID"
            onboarding.subscription_status = "ACTIVE"
            onboarding.payment_reference = payment.merchant_trade_no
            onboarding.payment_confirmed_at = datetime.utcnow()
            subscriber = (
                db.query(CopySubscriber)
                .filter(CopySubscriber.id == payment.subscriber_id)
                .first()
            )
            if subscriber is not None:
                subscriber.payment_status = "PAID"
            recompute_activation(db, onboarding)
    elif payload.get("bizStatus") == "PAY_CLOSED":
        payment.status = "CLOSED"

    db.commit()
    return {"returnCode": "SUCCESS", "returnMessage": None}


router.include_router(promo_router)
