"""Secure multi-platform broker-account linking routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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
    LiveAccessRequest,
)
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding
from api.subscription_lifecycle.models import SubscriptionAudit, SubscriptionLifecycle
from api.subscription_lifecycle.service import subscriber_can_copy


router = APIRouter(prefix="/broker-accounts", tags=["Broker Accounts"])

MASTER_BROKER_LOGIN = "49617874"
OWNER_SUBSCRIBER_LOGIN = "49224282"
OWNER_SUBSCRIBER_SERVER = "HFMGLOBALMARKETS-DEMO"


class ArchiveTestSubscribersRequest(BaseModel):
    confirmation: str = Field(min_length=20, max_length=100)


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

    currency = str(getattr(account, "currency", None) or "USD")
    cent_currency = currency.upper() in {"USC", "USCENT", "USCENTS", "CENT"}
    if data.account_type == "CENT" and not cent_currency:
        raise HTTPException(
            status_code=409,
            detail="Connected MT5 account does not report a supported cent currency",
        )

    return {
        "status": "CONNECTED",
        "server": actual_server or data.server,
        "currency": currency,
        "leverage": int(getattr(account, "leverage", 0) or 0),
        "last_verified_at": datetime.utcnow(),
        "capital_verified": data.account_type == "STANDARD" or cent_currency,
    }


def _prepare_connection(data: BrokerAccountLinkRequest):
    platform = data.platform
    capability = PLATFORM_CAPABILITIES[platform]

    if data.starting_capital_usd < 1000 and data.account_type != "CENT":
        raise HTTPException(
            status_code=422,
            detail="Starting capital below 1000 USD must use the Cent account pathway",
        )
    if data.account_type == "CENT" and platform not in {
        TradingPlatform.MT4,
        TradingPlatform.MT5,
    }:
        raise HTTPException(
            status_code=422,
            detail="Cent accounts are currently supported only on MT4 and MT5",
        )

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
            "capital_verified": False,
        }

    return {
        **result,
        "connection_method": capability["authorization"],
        "execution_mode": "PAPER",
    }


def _save_account(db: Session, subscriber_id: int, data: BrokerAccountLinkRequest):
    if data.login == MASTER_BROKER_LOGIN:
        raise HTTPException(
            status_code=409,
            detail="The master trading account cannot be linked as a subscriber",
        )

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
    account.account_type = data.account_type
    account.starting_capital_usd = data.starting_capital_usd
    account.capital_verified = prepared["capital_verified"]
    account.status = prepared["status"]
    account.connection_method = prepared["connection_method"]
    account.execution_mode = prepared["execution_mode"]
    account.live_authorized = False
    account.live_authorized_at = None
    account.live_authorized_by = None
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




@router.post("/admin/archive-test-subscribers")
def archive_test_subscribers(
    data: ArchiveTestSubscribersRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """Archive test subscribers while retaining financial and security audit history."""
    expected = f"ARCHIVE TEST SUBSCRIBERS KEEP {OWNER_SUBSCRIBER_LOGIN}"
    if data.confirmation != expected:
        raise HTTPException(status_code=422, detail=f"Confirmation must be: {expected}")

    owner_account = db.query(BrokerAccount).filter(
        BrokerAccount.login == OWNER_SUBSCRIBER_LOGIN
    ).first()
    if owner_account is None:
        raise HTTPException(
            status_code=409,
            detail="Owner broker account must be linked before test accounts can be archived",
        )
    if owner_account.server.casefold() != OWNER_SUBSCRIBER_SERVER.casefold():
        raise HTTPException(
            status_code=409,
            detail="Protected subscriber server does not match HFMGLOBALMARKETS-DEMO",
        )
    if "hfm" not in owner_account.broker.casefold() and "hfmarkets" not in owner_account.broker.casefold():
        raise HTTPException(
            status_code=409,
            detail="Protected subscriber account must be linked to HFM",
        )

    keep_subscriber_id = owner_account.subscriber_id
    archived_subscribers = 0
    archived_accounts = 0
    administrator = str(admin.get("email") or admin.get("sub") or "admin")

    subscribers = db.query(CopySubscriber).filter(
        CopySubscriber.id != keep_subscriber_id
    ).all()
    for subscriber in subscribers:
        if subscriber.status == "ARCHIVED":
            continue
        subscriber.status = "ARCHIVED"
        subscriber.synchronized = False
        archived_subscribers += 1

        accounts = db.query(BrokerAccount).filter(
            BrokerAccount.subscriber_id == subscriber.id
        ).all()
        for account in accounts:
            account.status = "ARCHIVED"
            account.execution_mode = "PAPER"
            account.live_authorized = False
            account.live_authorized_at = None
            account.live_authorized_by = None
            archived_accounts += 1

        onboarding = db.query(ClientOnboarding).filter(
            ClientOnboarding.subscriber_id == subscriber.id
        ).first()
        if onboarding is not None:
            onboarding.subscription_status = "SUSPENDED"
            onboarding.copy_trading_status = "INACTIVE"
            onboarding.admin_approval = "ARCHIVED"

        lifecycle = db.query(SubscriptionLifecycle).filter(
            SubscriptionLifecycle.subscriber_id == subscriber.id
        ).first()
        if lifecycle is not None:
            previous = lifecycle.status
            lifecycle.status = "SUSPENDED"
            lifecycle.manual_suspended = True
            lifecycle.suspended_at = datetime.utcnow()
            db.add(SubscriptionAudit(
                subscriber_id=subscriber.id,
                action="ARCHIVE_TEST",
                previous_status=previous,
                new_status="SUSPENDED",
                reference=lifecycle.last_payment_reference,
                administrator=administrator,
            ))

    owner_account.execution_mode = "PAPER"
    owner_account.live_authorized = False
    owner_account.live_authorized_at = None
    owner_account.live_authorized_by = None
    db.commit()
    return {
        "status": "success",
        "protected_broker_login": OWNER_SUBSCRIBER_LOGIN,
        "protected_server": owner_account.server,
        "protected_subscriber_id": keep_subscriber_id,
        "archived_subscribers": archived_subscribers,
        "archived_broker_accounts": archived_accounts,
        "owner_execution_mode": "PAPER",
    }


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


@router.post("/{account_id}/live-access", response_model=BrokerAccountResponse)
def set_live_access(
    account_id: int,
    data: LiveAccessRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Broker account not found")

    expected = "ENABLE LIVE MT5" if data.enabled else "DISABLE LIVE MT5"
    if data.confirmation != expected:
        raise HTTPException(status_code=422, detail=f"Confirmation must be: {expected}")

    if data.enabled:
        if account.platform != TradingPlatform.MT5.value:
            raise HTTPException(
                status_code=409,
                detail="Live access is currently available only for MT5 accounts",
            )
        if account.status != "CONNECTED":
            raise HTTPException(
                status_code=409,
                detail="MT5 account must be verified and connected",
            )
        if account.account_type == "CENT" and (
            account.starting_capital_usd is None
            or account.starting_capital_usd >= 1000
            or not account.capital_verified
        ):
            raise HTTPException(
                status_code=409,
                detail="Cent account capital and broker denomination must be verified",
            )
        if not subscriber_can_copy(db, account.subscriber_id):
            raise HTTPException(
                status_code=409,
                detail="Subscriber has not completed every activation requirement",
            )

    account.live_authorized = data.enabled
    account.execution_mode = "LIVE" if data.enabled else "PAPER"
    account.live_authorized_at = datetime.utcnow() if data.enabled else None
    account.live_authorized_by = (
        str(admin.get("email") or admin.get("sub") or "admin")
        if data.enabled
        else None
    )
    db.commit()
    db.refresh(account)
    return account
