"""
Bethel Trading Technologies

Secure Broker Account Linking Routes

Purpose:
    Verify and link a subscriber-controlled MT5 account.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin
from api.broker_accounts.models import BrokerAccount
from api.broker_accounts.schemas import (
    BrokerAccountCreate,
    BrokerAccountLinkRequest,
    BrokerAccountResponse,
)
from api.copytrading.models import CopySubscriber
from api.database import get_db
from mt5_connector.manager import MT5Manager
import MetaTrader5 as mt5


router = APIRouter(
    prefix="/broker-accounts",
    tags=["Broker Accounts"],
)


def _verified_terminal_account(data: BrokerAccountLinkRequest):
    if not MT5Manager.ensure_connection():
        raise HTTPException(status_code=503, detail="MT5 connection unavailable")

    account = mt5.account_info()
    if account is None:
        raise HTTPException(status_code=400, detail="Unable to read MT5 account")

    actual_login = str(account.login)
    actual_server = str(getattr(account, "server", "") or "")
    requested_login = str(data.login).strip()
    requested_server = str(data.server).strip()

    if requested_login != actual_login:
        raise HTTPException(
            status_code=409,
            detail="Submitted MT5 login does not match the connected terminal account",
        )
    if actual_server and requested_server.casefold() != actual_server.casefold():
        raise HTTPException(
            status_code=409,
            detail="Submitted MT5 server does not match the connected terminal server",
        )
    return account, actual_login, actual_server or requested_server


def _save_verified_account(
    db: Session,
    subscriber_id: int,
    data: BrokerAccountLinkRequest,
):
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    terminal, login, server = _verified_terminal_account(data)
    existing = (
        db.query(BrokerAccount)
        .filter(BrokerAccount.login == login)
        .first()
    )
    if existing and existing.subscriber_id != subscriber_id:
        raise HTTPException(
            status_code=409,
            detail="This MT5 account is already linked to another subscriber",
        )

    if existing is None:
        account = BrokerAccount(
            subscriber_id=subscriber_id,
            broker=data.broker,
            login=login,
            server=server,
        )
        db.add(account)
        db.flush()
    else:
        account = existing
        account.broker = data.broker
        account.server = server

    account.status = "CONNECTED"
    account.currency = getattr(terminal, "currency", None) or "USD"
    account.leverage = int(getattr(terminal, "leverage", 0) or 0)

    subscriber.broker = data.broker
    subscriber.mt5_account = login
    subscriber.mt5_account_id = account.id
    subscriber.synchronized = False

    db.commit()
    db.refresh(account)
    return account


@router.post(
    "/link/{subscriber_id}",
    response_model=BrokerAccountResponse,
)
def link_subscriber_broker_account(
    subscriber_id: int,
    data: BrokerAccountLinkRequest,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    return _save_verified_account(db, subscriber_id, data)


@router.post(
    "/link",
    response_model=BrokerAccountResponse,
    deprecated=True,
)
def admin_legacy_link(
    data: BrokerAccountCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    link_data = BrokerAccountLinkRequest(
        broker=data.broker,
        login=data.login,
        server=data.server,
    )
    return _save_verified_account(db, data.subscriber_id, link_data)


@router.get("/subscriber/{subscriber_id}")
def get_subscriber_broker_account(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    account = (
        db.query(BrokerAccount)
        .filter(BrokerAccount.subscriber_id == subscriber_id)
        .first()
    )
    if account is None:
        return {"status": "not_found"}
    return account
