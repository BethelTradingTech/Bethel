from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.broker_accounts.models import BrokerAccount
from api.copytrading.models import CopySubscriber
from api.profit_share.service import profit_share_accepted
from api.legal.service import all_current_accepted
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
    from api.subscription_lifecycle.service import enforce_subscription_state
    enforce_subscription_state(db, onboarding)
    from api.profit_share.service import profit_share_accepted
    from api.legal.service import all_current_accepted
    subscriber = get_subscriber(db, onboarding.subscriber_id)
    ready = all(
        (
            onboarding.subscription_status in ("ACTIVE", "GRACE"),
            onboarding.kyc_status == "APPROVED",
            onboarding.payment_status == "PAID",
            onboarding.broker_status == "CONNECTED",
            onboarding.admin_approval == "APPROVED",
            profit_share_accepted(db, onboarding.subscriber_id),
            all_current_accepted(db, onboarding.subscriber_id),
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
    from api.subscription_lifecycle.service import lifecycle_snapshot
    refresh_broker_status(db, onboarding)
    recompute_activation(db, onboarding)

    requirements = {
        "subscription": onboarding.subscription_status in ("ACTIVE", "GRACE"),
        "kyc": onboarding.kyc_status == "APPROVED",
        "payment": onboarding.payment_status == "PAID",
        "broker": onboarding.broker_status == "CONNECTED",
        "admin_approval": onboarding.admin_approval == "APPROVED",
        "profit_share": profit_share_accepted(db, onboarding.subscriber_id),
        "legal_consent": all_current_accepted(db, onboarding.subscriber_id),
    }

    broker_account = (
        db.query(BrokerAccount)
        .filter(BrokerAccount.subscriber_id == onboarding.subscriber_id)
        .first()
    )

    return {
        "subscriber_id": onboarding.subscriber_id,
        "subscription_lifecycle": lifecycle_snapshot(db, onboarding.subscriber_id),
        "plan_id": onboarding.plan_id,
        "subscription_status": onboarding.subscription_status,
        "kyc_status": onboarding.kyc_status,
        "payment_status": onboarding.payment_status,
        "payment_reference": onboarding.payment_reference,
        "broker_status": onboarding.broker_status,
        "broker_account": (
            {
                "id": broker_account.id,
                "platform": broker_account.platform,
                "broker": broker_account.broker,
                "login": broker_account.login,
                "server": broker_account.server,
                "execution_mode": broker_account.execution_mode,
                "live_authorized": broker_account.live_authorized,
            }
            if broker_account
            else None
        ),
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
