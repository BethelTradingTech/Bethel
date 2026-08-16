from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from api.auth.dependency import require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding.service import get_or_create_onboarding, initial_charge, recompute_activation, satisfy_activation_fee
from api.stripe_payments.models import StripePayment
from api.stripe_payments.stripe_api import create_checkout_session, verify_webhook


router = APIRouter(prefix="/payments/stripe", tags=["Stripe Card Payments"])


def reconcile_paid_checkout(
    db: Session,
    payment: StripePayment,
    session: dict,
    subscriber_id: int,
    plan_id: int,
):
    if payment.subscriber_id != subscriber_id or payment.plan_id != plan_id:
        raise HTTPException(status_code=409, detail="Stripe payment identity mismatch")

    expected_minor = int(round(payment.amount * 100))
    if session.get("amount_total") != expected_minor:
        raise HTTPException(status_code=409, detail="Stripe payment amount mismatch")
    if str(session.get("currency", "")).upper() != payment.currency.upper():
        raise HTTPException(status_code=409, detail="Stripe payment currency mismatch")

    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding is None or onboarding.plan_id != plan_id:
        raise HTTPException(status_code=409, detail="Subscription selection changed")

    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == subscriber_id).first()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    now = payment.paid_at or datetime.utcnow()
    payment.status = "PAID"
    payment.payment_intent_id = session.get("payment_intent") or payment.payment_intent_id
    payment.paid_at = now
    onboarding.payment_status = "PAID"
    onboarding.subscription_status = "ACTIVE"
    onboarding.payment_reference = f"STRIPE:{payment.checkout_session_id}"
    onboarding.payment_confirmed_at = now
    satisfy_activation_fee(onboarding, now)
    subscriber.payment_status = "PAID"
    recompute_activation(db, onboarding)
    db.commit()


@router.post("/{subscriber_id}/checkout")
def create_card_checkout(
    subscriber_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == subscriber_id).first()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    onboarding = get_or_create_onboarding(db, subscriber_id)
    if onboarding.plan_id is None:
        raise HTTPException(status_code=409, detail="Select a subscription plan first")
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == onboarding.plan_id, SubscriptionPlan.active.is_(True)).first()
    if plan is None:
        raise HTTPException(status_code=409, detail="Subscription plan is unavailable")

    charge = initial_charge(db, onboarding, plan)
    plan_amount = charge["subscription_amount"]
    activation_fee = charge["activation_fee"]
    total_amount = charge["total_amount"]
    currency = charge["currency"].lower()
    if plan_amount <= 0:
        raise HTTPException(status_code=409, detail="Invalid subscription price")

    reference = f"BTT-{subscriber_id}-{secrets.token_hex(8)}"
    base = str(request.base_url).rstrip("/")
    fields = {
        "mode": "payment",
        "payment_method_types[0]": "card",
        "success_url": f"{base}/investor-frontend/onboarding.html?payment=stripe-success&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/investor-frontend/onboarding.html?payment=stripe-cancelled",
        "client_reference_id": reference,
        "customer_email": subscriber.email,
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": currency,
        "line_items[0][price_data][unit_amount]": str(int(round(plan_amount * 100))),
        "line_items[0][price_data][product_data][name]": f"Bethel {plan.name} subscription",
        "metadata[subscriber_id]": str(subscriber_id),
        "metadata[plan_id]": str(plan.id),
        "metadata[reference]": reference,
        "metadata[plan_amount]": f"{plan_amount:.2f}",
        "metadata[activation_fee]": f"{activation_fee:.2f}",
    }
    if activation_fee > 0:
        fields.update({
            "line_items[1][quantity]": "1",
            "line_items[1][price_data][currency]": currency,
            "line_items[1][price_data][unit_amount]": str(int(round(activation_fee * 100))),
            "line_items[1][price_data][product_data][name]": "Bethel one-time activation fee",
        })
    session = create_checkout_session(fields)
    session_id = session.get("id")
    checkout_url = session.get("url")
    if not session_id or not checkout_url:
        raise HTTPException(status_code=502, detail="Stripe returned an invalid checkout")

    payment = StripePayment(subscriber_id=subscriber_id, plan_id=plan.id, checkout_session_id=session_id, amount=total_amount, currency=charge["currency"], status="PENDING", checkout_url=checkout_url)
    db.add(payment)
    db.commit()
    return {"status": payment.status, "checkout_session_id": session_id, "checkout_url": checkout_url, **charge}


@router.get("/{subscriber_id}/latest")
def latest_card_payment(subscriber_id: int, db: Session = Depends(get_db), _actor=Depends(require_subscriber_or_admin)):
    payment = db.query(StripePayment).filter(StripePayment.subscriber_id == subscriber_id).order_by(StripePayment.id.desc()).first()
    if payment is None:
        return {"status": "not_found"}
    return {"status": payment.status, "checkout_session_id": payment.checkout_session_id, "amount": payment.amount, "currency": payment.currency, "paid_at": payment.paid_at}


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(default="", alias="Stripe-Signature"), db: Session = Depends(get_db)):
    raw_body = await request.body()
    event = verify_webhook(raw_body, stripe_signature)
    if event.get("type") not in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        return {"received": True}
    session = event.get("data", {}).get("object", {})
    if session.get("payment_status") != "paid":
        return {"received": True}
    metadata = session.get("metadata") or {}
    try:
        subscriber_id = int(metadata["subscriber_id"])
        plan_id = int(metadata["plan_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Missing Stripe payment metadata") from exc
    payment = db.query(StripePayment).filter(StripePayment.checkout_session_id == session.get("id")).first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Stripe payment record not found")
    reconcile_paid_checkout(db, payment, session, subscriber_id, plan_id)
    return {"received": True, "reconciled": True, "subscriber_id": subscriber_id}
