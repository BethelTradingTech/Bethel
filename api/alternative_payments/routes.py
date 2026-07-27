from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.alternative_payments.models import PayPalPayment, WisePayment
from api.alternative_payments.paypal_api import capture_order, create_order
from api.auth.dependency import require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding.service import get_or_create_onboarding, recompute_activation


router = APIRouter(tags=["PayPal and Wise Payments"])


class WiseReference(BaseModel):
    reference: str = Field(min_length=4, max_length=150)


def subscriber_and_plan(db: Session, subscriber_id: int):
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
        .filter(
            SubscriptionPlan.id == onboarding.plan_id,
            SubscriptionPlan.active.is_(True),
        )
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=409, detail="Subscription plan is unavailable")
    return subscriber, onboarding, plan


def mark_paid(db: Session, payment: PayPalPayment, capture: dict):
    amount = capture.get("amount") or {}
    if capture.get("status") != "COMPLETED":
        raise HTTPException(status_code=409, detail="PayPal payment is not completed")
    if amount.get("currency_code", "").upper() != payment.currency.upper():
        raise HTTPException(status_code=409, detail="PayPal currency mismatch")
    try:
        captured_amount = float(amount.get("value"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Invalid PayPal amount") from exc
    if abs(captured_amount - payment.amount) > 0.005:
        raise HTTPException(status_code=409, detail="PayPal amount mismatch")

    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == payment.subscriber_id)
        .first()
    )
    if onboarding is None or onboarding.plan_id != payment.plan_id:
        raise HTTPException(status_code=409, detail="Subscription selection changed")
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == payment.subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    now = datetime.utcnow()
    payment.status = "PAID"
    payment.capture_id = capture.get("id")
    payment.paid_at = now
    onboarding.payment_status = "PAID"
    onboarding.subscription_status = "ACTIVE"
    onboarding.payment_reference = f"PAYPAL:{payment.order_id}"
    onboarding.payment_confirmed_at = now
    subscriber.payment_status = "PAID"
    recompute_activation(db, onboarding)
    db.commit()


@router.post("/payments/paypal/{subscriber_id}/order")
def paypal_order(
    subscriber_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    subscriber, _onboarding, plan = subscriber_and_plan(db, subscriber_id)
    currency = (plan.currency or "USD").upper()
    amount = f"{float(plan.price):.2f}"
    base = str(request.base_url).rstrip("/")
    result = create_order(
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": f"subscriber-{subscriber_id}-plan-{plan.id}",
                    "description": f"Bethel {plan.name} subscription",
                    "custom_id": f"{subscriber_id}:{plan.id}",
                    "amount": {"currency_code": currency, "value": amount},
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "brand_name": "Bethel Trading Technologies",
                        "user_action": "PAY_NOW",
                        "return_url": (
                            f"{base}/investor-frontend/onboarding.html"
                            "?payment=paypal-success"
                        ),
                        "cancel_url": (
                            f"{base}/investor-frontend/onboarding.html"
                            "?payment=paypal-cancelled"
                        ),
                    }
                }
            },
        }
    )
    order_id = result.get("id")
    approval_url = next(
        (link.get("href") for link in result.get("links", []) if link.get("rel") == "payer-action"),
        None,
    )
    if not order_id or not approval_url:
        raise HTTPException(status_code=502, detail="PayPal returned an invalid order")
    payment = PayPalPayment(
        subscriber_id=subscriber_id,
        plan_id=plan.id,
        order_id=order_id,
        amount=float(plan.price),
        currency=currency,
        status="CREATED",
        approval_url=approval_url,
    )
    db.add(payment)
    db.commit()
    return {
        "status": payment.status,
        "order_id": order_id,
        "approval_url": approval_url,
        "amount": payment.amount,
        "currency": payment.currency,
    }


@router.post("/payments/paypal/{subscriber_id}/capture/{order_id}")
def paypal_capture(
    subscriber_id: int,
    order_id: str,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    payment = (
        db.query(PayPalPayment)
        .filter(
            PayPalPayment.subscriber_id == subscriber_id,
            PayPalPayment.order_id == order_id,
        )
        .first()
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="PayPal order not found")
    if payment.status == "PAID":
        return {"status": "PAID", "order_id": order_id}
    result = capture_order(order_id)
    captures = (
        result.get("purchase_units", [{}])[0]
        .get("payments", {})
        .get("captures", [])
    )
    if not captures:
        raise HTTPException(status_code=409, detail="PayPal returned no completed capture")
    mark_paid(db, payment, captures[0])
    return {"status": "PAID", "order_id": order_id}


@router.get("/payments/paypal/{subscriber_id}/latest")
def paypal_latest(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    payment = (
        db.query(PayPalPayment)
        .filter(PayPalPayment.subscriber_id == subscriber_id)
        .order_by(PayPalPayment.id.desc())
        .first()
    )
    if payment is None:
        return {"status": "not_found"}
    return {
        "status": payment.status,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "paid_at": payment.paid_at,
    }


def wise_settings():
    settings = {
        "recipient_name": os.getenv("WISE_RECIPIENT_NAME", ""),
        "bank_name": os.getenv("WISE_BANK_NAME", ""),
        "account_number": os.getenv("WISE_ACCOUNT_NUMBER", ""),
        "iban": os.getenv("WISE_IBAN", ""),
        "swift_bic": os.getenv("WISE_SWIFT_BIC", ""),
        "currency": os.getenv("WISE_CURRENCY", "USD"),
    }
    if not settings["recipient_name"] or not settings["bank_name"]:
        raise HTTPException(
            status_code=503,
            detail="Wise Business recipient details are not configured",
        )
    if not settings["account_number"] and not settings["iban"]:
        raise HTTPException(
            status_code=503,
            detail="Wise Business account details are not configured",
        )
    return settings


@router.get("/payments/wise/{subscriber_id}/instructions")
def wise_instructions(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    _subscriber, _onboarding, plan = subscriber_and_plan(db, subscriber_id)
    settings = wise_settings()
    return {
        **settings,
        "amount": float(plan.price),
        "plan_currency": (plan.currency or "USD").upper(),
        "message": "Transfer the exact amount and submit your Wise reference",
    }


@router.post("/payments/wise/{subscriber_id}/submit")
def wise_submit(
    subscriber_id: int,
    data: WiseReference,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    _subscriber, onboarding, plan = subscriber_and_plan(db, subscriber_id)
    settings = wise_settings()
    reference = data.reference.strip()
    duplicate = (
        db.query(WisePayment)
        .filter(WisePayment.reference == reference)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Wise reference already submitted")
    payment = WisePayment(
        subscriber_id=subscriber_id,
        plan_id=plan.id,
        reference=reference,
        amount=float(plan.price),
        currency=settings["currency"].upper(),
    )
    db.add(payment)
    onboarding.payment_status = "PENDING_VERIFICATION"
    onboarding.payment_reference = f"WISE:{reference}"
    onboarding.payment_confirmed_at = None
    db.commit()
    return {
        "status": "PENDING_VERIFICATION",
        "reference": reference,
        "message": "Wise transfer submitted for administrator verification",
    }
