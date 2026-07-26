from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.broker_accounts.models import BrokerAccount
from api.copytrading.models import CopySubscriber
from api.onboarding.models import ClientOnboarding


def get_subscriber(db: Session, subscriber_id: int):
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber


def get_or_create_onboarding(db: Session, subscriber_id: int):
    get_subscriber(db, subscriber_id)
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding is None:
        onboarding = ClientOnboarding(subscriber_id=subscriber_id)
        db.add(onboarding)
        db.flush()
    return onboarding


def refresh_broker_status(db: Session, onboarding: ClientOnboarding):
    account = (
        db.query(BrokerAccount)
        .filter(
            BrokerAccount.subscriber_id == onboarding.subscriber_id,
            BrokerAccount.status == "CONNECTED",
        )
        .first()
    )
    onboarding.broker_status = "CONNECTED" if account else "NOT_CONNECTED"


def recompute_activation(db: Session, onboarding: ClientOnboarding):
    subscriber = get_subscriber(db, onboarding.subscriber_id)
    ready = all(
        (
            onboarding.subscription_status == "ACTIVE",
            onboarding.kyc_status == "APPROVED",
            onboarding.payment_status == "PAID",
            onboarding.broker_status == "CONNECTED",
            onboarding.admin_approval == "APPROVED",
        )
    )

    if ready:
        onboarding.copy_trading_status = "ACTIVE"
        onboarding.activated_at = onboarding.activated_at or datetime.utcnow()
        subscriber.status = "ACTIVE"
        subscriber.payment_status = "PAID"
        subscriber.activated_at = subscriber.activated_at or datetime.utcnow()
    else:
        onboarding.copy_trading_status = "INACTIVE"
        onboarding.activated_at = None
        if subscriber.status == "ACTIVE":
            subscriber.status = "PENDING"

    return ready


def serialize_onboarding(db: Session, onboarding: ClientOnboarding):
    refresh_broker_status(db, onboarding)
    recompute_activation(db, onboarding)

    requirements = {
        "subscription": onboarding.subscription_status == "ACTIVE",
        "kyc": onboarding.kyc_status == "APPROVED",
        "payment": onboarding.payment_status == "PAID",
        "broker": onboarding.broker_status == "CONNECTED",
        "admin_approval": onboarding.admin_approval == "APPROVED",
    }

    return {
        "subscriber_id": onboarding.subscriber_id,
        "plan_id": onboarding.plan_id,
        "subscription_status": onboarding.subscription_status,
        "kyc_status": onboarding.kyc_status,
        "payment_status": onboarding.payment_status,
        "payment_reference": onboarding.payment_reference,
        "broker_status": onboarding.broker_status,
        "admin_approval": onboarding.admin_approval,
        "copy_trading_status": onboarding.copy_trading_status,
        "rejection_reason": onboarding.rejection_reason,
        "requirements": requirements,
        "ready_for_activation": all(requirements.values()),
        "activated_at": (
            onboarding.activated_at.isoformat()
            if onboarding.activated_at
            else None
        ),
    }
