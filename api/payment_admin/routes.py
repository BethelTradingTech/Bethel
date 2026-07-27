from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.alternative_payments.models import PayPalPayment, WisePayment
from api.auth.dependency import require_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding.service import recompute_activation
from api.payment_admin.models import PaymentAudit
from api.payments.models import BinancePayment
from api.stripe_payments.models import StripePayment


router = APIRouter(prefix="/admin/payments", tags=["Admin Payment Reconciliation"])


class ReconciliationDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=500)


def iso(value):
    return value.isoformat() + "Z" if value else None


def subscriber_map(db: Session):
    return {
        row.id: {"name": row.name, "email": row.email}
        for row in db.query(CopySubscriber).all()
    }


def normalized_rows(db: Session):
    subscribers = subscriber_map(db)
    rows = []

    for payment in db.query(StripePayment).all():
        person = subscribers.get(payment.subscriber_id, {})
        rows.append({
            "record_key": f"STRIPE:{payment.id}",
            "method": "STRIPE",
            "payment_id": str(payment.id),
            "subscriber_id": payment.subscriber_id,
            "subscriber_name": person.get("name"),
            "subscriber_email": person.get("email"),
            "plan_id": payment.plan_id,
            "reference": payment.checkout_session_id,
            "provider_transaction": payment.payment_intent_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "created_at": iso(payment.created_at),
            "paid_at": iso(payment.paid_at),
            "admin_action": False,
        })

    for payment in db.query(PayPalPayment).all():
        person = subscribers.get(payment.subscriber_id, {})
        rows.append({
            "record_key": f"PAYPAL:{payment.id}",
            "method": "PAYPAL",
            "payment_id": str(payment.id),
            "subscriber_id": payment.subscriber_id,
            "subscriber_name": person.get("name"),
            "subscriber_email": person.get("email"),
            "plan_id": payment.plan_id,
            "reference": payment.order_id,
            "provider_transaction": payment.capture_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "created_at": iso(payment.created_at),
            "paid_at": iso(payment.paid_at),
            "admin_action": False,
        })

    for payment in db.query(BinancePayment).all():
        person = subscribers.get(payment.subscriber_id, {})
        rows.append({
            "record_key": f"BINANCE:{payment.id}",
            "method": "BINANCE_USDT",
            "payment_id": str(payment.id),
            "subscriber_id": payment.subscriber_id,
            "subscriber_name": person.get("name"),
            "subscriber_email": person.get("email"),
            "plan_id": payment.plan_id,
            "reference": payment.merchant_trade_no,
            "provider_transaction": payment.transaction_id or payment.prepay_id,
            "amount": payment.fiat_amount,
            "currency": payment.fiat_currency,
            "status": payment.status,
            "created_at": iso(payment.created_at),
            "paid_at": iso(payment.paid_at),
            "admin_action": False,
        })

    for payment in db.query(WisePayment).all():
        person = subscribers.get(payment.subscriber_id, {})
        rows.append({
            "record_key": f"WISE:{payment.id}",
            "method": "WISE",
            "payment_id": str(payment.id),
            "subscriber_id": payment.subscriber_id,
            "subscriber_name": person.get("name"),
            "subscriber_email": person.get("email"),
            "plan_id": payment.plan_id,
            "reference": payment.reference,
            "provider_transaction": None,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "created_at": iso(payment.created_at),
            "paid_at": iso(payment.verified_at),
            "admin_action": payment.status == "PENDING_VERIFICATION",
        })

    known_prefixes = ("STRIPE:", "PAYPAL:", "BINANCE:", "WISE:")
    onboarding_rows = (
        db.query(ClientOnboarding, SubscriptionPlan)
        .outerjoin(SubscriptionPlan, SubscriptionPlan.id == ClientOnboarding.plan_id)
        .filter(ClientOnboarding.payment_reference.isnot(None))
        .all()
    )
    for onboarding, plan in onboarding_rows:
        reference = onboarding.payment_reference or ""
        if reference.upper().startswith(known_prefixes):
            continue
        person = subscribers.get(onboarding.subscriber_id, {})
        rows.append({
            "record_key": f"MANUAL:{onboarding.subscriber_id}",
            "method": "MANUAL",
            "payment_id": str(onboarding.subscriber_id),
            "subscriber_id": onboarding.subscriber_id,
            "subscriber_name": person.get("name"),
            "subscriber_email": person.get("email"),
            "plan_id": onboarding.plan_id,
            "reference": reference,
            "provider_transaction": None,
            "amount": plan.price if plan else None,
            "currency": plan.currency if plan else None,
            "status": onboarding.payment_status,
            "created_at": iso(onboarding.updated_at),
            "paid_at": iso(onboarding.payment_confirmed_at),
            "admin_action": onboarding.payment_status == "PENDING_VERIFICATION",
        })

    rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return rows


@router.get("")
def payment_history(
    method: str | None = Query(default=None),
    status: str | None = Query(default=None),
    subscriber_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    rows = normalized_rows(db)
    if method:
        rows = [row for row in rows if row["method"] == method.upper()]
    if status:
        rows = [row for row in rows if row["status"] == status.upper()]
    if subscriber_id is not None:
        rows = [row for row in rows if row["subscriber_id"] == subscriber_id]

    totals = {}
    for row in rows:
        if row["status"] in ("PAID", "PAY_SUCCESS", "COMPLETED") and row["amount"] is not None:
            currency = (row["currency"] or "UNKNOWN").upper()
            totals[currency] = round(totals.get(currency, 0) + float(row["amount"]), 2)
    return {
        "status": "success",
        "total": len(rows),
        "pending_review": sum(1 for row in rows if row["status"] == "PENDING_VERIFICATION"),
        "paid": sum(1 for row in rows if row["status"] in ("PAID", "PAY_SUCCESS", "COMPLETED")),
        "rejected": sum(1 for row in rows if row["status"] == "REJECTED"),
        "paid_totals_by_currency": totals,
        "payments": rows,
    }


def audit(
    db: Session,
    *,
    method: str,
    payment_id: str,
    subscriber_id: int,
    previous_status: str,
    new_status: str,
    admin: dict,
    reason: str | None,
):
    db.add(PaymentAudit(
        method=method,
        payment_id=payment_id,
        subscriber_id=subscriber_id,
        action="VERIFY" if new_status == "PAID" else "REJECT",
        previous_status=previous_status,
        new_status=new_status,
        administrator=str(admin.get("email") or admin.get("sub") or "admin"),
        reason=reason,
    ))


def update_onboarding(
    db: Session,
    subscriber_id: int,
    reference: str,
    approved: bool,
):
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding is None:
        raise HTTPException(status_code=404, detail="Onboarding record not found")
    now = datetime.utcnow()
    if approved:
        onboarding.payment_status = "PAID"
        onboarding.subscription_status = "ACTIVE"
        onboarding.payment_confirmed_at = now
        subscriber = (
            db.query(CopySubscriber)
            .filter(CopySubscriber.id == subscriber_id)
            .first()
        )
        if subscriber is None:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        subscriber.payment_status = "PAID"
    else:
        onboarding.payment_status = "REJECTED"
        onboarding.subscription_status = "PENDING_PAYMENT"
        onboarding.payment_confirmed_at = None
    onboarding.payment_reference = reference
    recompute_activation(db, onboarding)


@router.post("/wise/{payment_id}/decision")
def decide_wise_payment(
    payment_id: int,
    data: ReconciliationDecision,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    payment = (
        db.query(WisePayment)
        .filter(WisePayment.id == payment_id)
        .first()
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Wise payment not found")
    if payment.status != "PENDING_VERIFICATION":
        raise HTTPException(status_code=409, detail="Wise payment is not pending review")
    approved = data.decision == "APPROVED"
    previous = payment.status
    payment.status = "PAID" if approved else "REJECTED"
    payment.verified_at = datetime.utcnow() if approved else None
    update_onboarding(
        db,
        payment.subscriber_id,
        f"WISE:{payment.reference}",
        approved,
    )
    audit(
        db,
        method="WISE",
        payment_id=str(payment.id),
        subscriber_id=payment.subscriber_id,
        previous_status=previous,
        new_status=payment.status,
        admin=admin,
        reason=data.reason,
    )
    db.commit()
    return {"status": payment.status}


@router.post("/manual/{subscriber_id}/decision")
def decide_manual_payment(
    subscriber_id: int,
    data: ReconciliationDecision,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding is None or not onboarding.payment_reference:
        raise HTTPException(status_code=404, detail="Manual payment submission not found")
    if onboarding.payment_status != "PENDING_VERIFICATION":
        raise HTTPException(status_code=409, detail="Manual payment is not pending review")
    if onboarding.payment_reference.upper().startswith(
        ("STRIPE:", "PAYPAL:", "BINANCE:", "WISE:")
    ):
        raise HTTPException(status_code=409, detail="Provider payment cannot be manually approved")
    approved = data.decision == "APPROVED"
    previous = onboarding.payment_status
    reference = onboarding.payment_reference
    update_onboarding(db, subscriber_id, reference, approved)
    audit(
        db,
        method="MANUAL",
        payment_id=str(subscriber_id),
        subscriber_id=subscriber_id,
        previous_status=previous,
        new_status="PAID" if approved else "REJECTED",
        admin=admin,
        reason=data.reason,
    )
    db.commit()
    return {"status": "PAID" if approved else "REJECTED"}


@router.get("/audit")
def payment_audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    rows = (
        db.query(PaymentAudit)
        .order_by(PaymentAudit.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "status": "success",
        "audit": [
            {
                "id": row.id,
                "method": row.method,
                "payment_id": row.payment_id,
                "subscriber_id": row.subscriber_id,
                "action": row.action,
                "previous_status": row.previous_status,
                "new_status": row.new_status,
                "administrator": row.administrator,
                "reason": row.reason,
                "created_at": iso(row.created_at),
            }
            for row in rows
        ],
    }
