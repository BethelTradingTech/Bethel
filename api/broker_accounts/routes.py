"""Secure multi-platform broker-account linking routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin
from api.broker_accounts.models import BrokerAccount
from api.broker_accounts.platforms import (
    PLATFORM_CAPABILITIES,
    TradingPlatform,
    platform_capabilities,
)
from api.broker_accounts.schemas import (
    BrokerAccountCreate,
    BrokerAccountLinkRequest,
    BrokerAccountResponse,
)
from api.copytrading.models import CopySubscriber
from api.database import get_db


router = APIRouter(prefix="/broker-accounts", tags=["Broker Accounts"])


def _verify_mt5_terminal(data: BrokerAccountLinkRequest):
    # MT5 remains the only locally verifiable adapter in this deployment.
    from mt5_connector.manager import MT5Manager
    import MetaTrader5 as mt5

    if not MT5Manager.ensure_connection():
        raise HTTPException(status_code=503, detail="MT5 connection unavailable")

    account = mt5.account_info()
    if account is None:
        raise HTTPException(status_code=400, detail="Unable to read MT5 account")

    actual_login = str(account.login)
    actual_server = str(getattr(account, "server", "") or "")
    if data.login != actual_login:
        raise HTTPException(
            status_code=409,
            detail="Submitted MT5 login does not match the connected terminal account",
        )
    if actual_server and data.server.casefold() != actual_server.casefold():
        raise HTTPException(
            status_code=409,
            detail="Submitted MT5 server does not match the connected terminal server",
        )

    return {
        "status": "CONNECTED",
        "server": actual_server or data.server,
        "currency": getattr(account, "currency", None) or "USD",
        "leverage": int(getattr(account, "leverage", 0) or 0),
        "last_verified_at": datetime.utcnow(),
    }


def _prepare_connection(data: BrokerAccountLinkRequest):
    platform = data.platform
    capability = PLATFORM_CAPABILITIES[platform]

    if platform == TradingPlatform.MT5:
        result = _verify_mt5_terminal(data)
    else:
        # Never collect or store trading passwords. MT4 requires the Bethel bridge
        # agent; cTrader requires OAuth; Match-Trader requires an approved broker
        # API. Those adapters authorize asynchronously.
        result = {
            "status": "PENDING_AUTHORIZATION",
            "server": data.server,
            "currency": "USD",
            "leverage": 0,
            "last_verified_at": None,
        }

    return {
        **result,
        "connection_method": capability["authorization"],
        "execution_mode": "PAPER",
    }


def _save_account(db: Session, subscriber_id: int, data: BrokerAccountLinkRequest):
    subscriber = db.query(CopySubscriber).filter(
        CopySubscriber.id == subscriber_id
    ).first()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    platform = data.platform.value
    existing = db.query(BrokerAccount).filter(
        BrokerAccount.login == data.login
    ).first()
    if existing and existing.subscriber_id != subscriber_id:
        raise HTTPException(
            status_code=409,
            detail="This trading account is already linked to another subscriber",
        )
    if existing and existing.platform != platform:
        raise HTTPException(
            status_code=409,
            detail="This account identifier is already linked on another platform",
        )

    prepared = _prepare_connection(data)
    account = existing or BrokerAccount(
        subscriber_id=subscriber_id,
        login=data.login,
    )
    if existing is None:
        db.add(account)

    account.platform = platform
    account.broker = data.broker
    account.server = prepared["server"]
    account.status = prepared["status"]
    account.connection_method = prepared["connection_method"]
    account.execution_mode = prepared["execution_mode"]
    account.currency = prepared["currency"]
    account.leverage = prepared["leverage"]
    account.last_verified_at = prepared["last_verified_at"]

    # Keep legacy subscriber fields populated until all consumers are migrated.
    subscriber.broker = data.broker
    subscriber.mt5_account = data.login
    subscriber.synchronized = False

    db.flush()
    subscriber.mt5_account_id = account.id
    db.commit()
    db.refresh(account)
    return account


@router.get("/platforms")
def list_supported_platforms():
    return {"mode": "PAPER", "platforms": platform_capabilities()}


@router.post("/link/{subscriber_id}", response_model=BrokerAccountResponse)
def link_subscriber_broker_account(
    subscriber_id: int,
    data: BrokerAccountLinkRequest,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    return _save_account(db, subscriber_id, data)


@router.post("/link", response_model=BrokerAccountResponse, deprecated=True)
def admin_legacy_link(
    data: BrokerAccountCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    return _save_account(db, data.subscriber_id, data)


@router.get("/subscriber/{subscriber_id}")
def get_subscriber_broker_account(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    account = db.query(BrokerAccount).filter(
        BrokerAccount.subscriber_id == subscriber_id
    ).first()
    return account or {"status": "not_found"}
