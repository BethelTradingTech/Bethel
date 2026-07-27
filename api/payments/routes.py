import json
import secrets
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from api.auth.dependency import require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding.service import get_or_create_onboarding, recompute_activation
from api.payments.binance_client import signed_post, verify_webhook
from api.payments.models import BinancePayment


router = APIRouter(prefix="/payments/binance", tags=["Binance Pay USDT"])


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
