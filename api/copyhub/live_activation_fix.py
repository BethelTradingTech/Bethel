"""Compatibility activation route for LIVE MT5 receiver verification.

A LIVE terminal may prove possession and establish its encrypted receiver token
before Super Admin live authorization. The receiver remains inactive and paused,
so this route never enables copying or live execution by itself.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.broker_accounts.models import BrokerAccount
from api.copyhub.models import CopyReceiver, ReceiverActivation
from api.database import get_db


router = APIRouter(prefix="/copyhub/v1", tags=["Secure Copy Hub"])


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class CustomerActivationRequest(BaseModel):
    activation_code: str = Field(min_length=20, max_length=120)
    account_number: str = Field(min_length=5, max_length=32)
    environment: str = Field(pattern="^(DEMO|LIVE)$")
    currency_unit: str = Field(pattern="^(USD|USC)$")
    is_cent_account: bool
    contract_size: float = Field(gt=0)
    min_lot: float = Field(gt=0)
    max_lot: float = Field(gt=0)
    lot_step: float = Field(gt=0)
    server: str | None = Field(default=None, min_length=2, max_length=255)
    leverage: int | None = Field(default=None, ge=0, le=10000)


@router.post("/receiver/activate")
def customer_activate_live_safe(
    data: CustomerActivationRequest,
    db: Session = Depends(get_db),
):
    activation = db.query(ReceiverActivation).filter(
        ReceiverActivation.code_hash == token_hash(data.activation_code.strip()),
        ReceiverActivation.used_at.is_(None),
    ).first()
    if activation is None:
        raise HTTPException(401, "Invalid or already used activation code")

    activation.attempts += 1
    if activation.attempts > 5 or activation.expires_at < utc_now():
        db.commit()
        raise HTTPException(401, "Activation code has expired")

    receiver = db.query(CopyReceiver).filter(
        CopyReceiver.id == activation.receiver_id
    ).first()
    if receiver is None or data.account_number != receiver.account_number:
        db.commit()
        raise HTTPException(409, "MT5 account does not match this activation")

    # Earlier broker linking intentionally provisioned every unapproved LIVE
    # account as DEMO. The Windows Copier correctly detects the real terminal as
    # LIVE, producing a permanent mismatch. Permit only this one-way correction
    # while the receiver is still inactive and paused. This verifies possession;
    # it does not authorize copying.
    if data.environment != receiver.environment:
        safe_live_promotion = (
            receiver.environment == "DEMO"
            and data.environment == "LIVE"
            and not receiver.active
            and receiver.paused
            and not receiver.live_authorized
        )
        if not safe_live_promotion:
            db.commit()
            raise HTTPException(409, "MT5 DEMO/LIVE mode does not match this activation")
        receiver.environment = "LIVE"

    if data.currency_unit != receiver.currency_unit or data.is_cent_account != receiver.is_cent_account:
        db.commit()
        raise HTTPException(409, "MT5 USD/USC account type does not match this activation")

    raw_token = secrets.token_urlsafe(48)
    receiver.token_hash = token_hash(raw_token)
    receiver.contract_size = data.contract_size
    receiver.min_lot = data.min_lot
    receiver.max_lot = data.max_lot
    receiver.lot_step = data.lot_step
    receiver.metadata_verified = True
    receiver.last_heartbeat_at = utc_now()

    # Explicitly preserve the safety gates. Super Admin approval remains a
    # separate action and is still required before any events can be delivered.
    receiver.active = False
    receiver.paused = True
    if receiver.environment == "LIVE":
        receiver.live_authorized = False

    account = db.query(BrokerAccount).filter(
        BrokerAccount.id == receiver.broker_account_id
    ).first()
    if account is not None:
        account.status = "CONNECTED"
        account.currency = data.currency_unit
        account.account_type = "CENT" if data.is_cent_account else "STANDARD"
        account.capital_verified = True
        account.last_verified_at = utc_now()
        if data.server:
            account.server = data.server
        if data.leverage is not None:
            account.leverage = data.leverage

    activation.used_at = utc_now()
    db.commit()
    return {
        "status": "activated",
        "receiver_id": receiver.receiver_id,
        "receiver_token": raw_token,
        "token_shown_once": True,
        "active": False,
        "paused": True,
        "terminal_verified": True,
        "live_authorization_required": receiver.environment == "LIVE",
    }
