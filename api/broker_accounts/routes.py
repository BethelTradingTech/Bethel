"""
Bethel Trading Technologies

Broker Account Linking Routes

Purpose:
    Link subscriber MT5 accounts.

Mode:
    Copy Trading Infrastructure
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db

from api.broker_accounts.models import BrokerAccount
from api.broker_accounts.schemas import (
    BrokerAccountCreate,
    BrokerAccountResponse
)

from mt5_connector.manager import MT5Manager
import MetaTrader5 as mt5


router = APIRouter(
    prefix="/broker-accounts",
    tags=["Broker Accounts"]
)



@router.post(
    "/link",
    response_model=BrokerAccountResponse
)
def link_broker_account(
    data: BrokerAccountCreate,
    db: Session = Depends(get_db)
):

    # Ensure MT5 terminal is available
    connected = MT5Manager.ensure_connection()

    if not connected:
        raise HTTPException(
            status_code=500,
            detail="MT5 connection unavailable"
        )


    # Check subscriber account information
    account = mt5.account_info()


    if account is None:

        raise HTTPException(
            status_code=400,
            detail="Unable to read MT5 account"
        )


    # Prevent duplicate linking
    existing = (
        db.query(BrokerAccount)
        .filter(
            BrokerAccount.login == data.login
        )
        .first()
    )


    if existing:

        existing.server = data.server
        existing.status = "CONNECTED"

        db.commit()
        db.refresh(existing)

        return existing



    new_account = BrokerAccount(

        subscriber_id=data.subscriber_id,

        broker=data.broker,

        login=data.login,

        server=data.server,

        status="CONNECTED",

        currency=account.currency,

        leverage=account.leverage

    )


    db.add(new_account)

    db.commit()

    db.refresh(new_account)


    return new_account



@router.get(
    "/subscriber/{subscriber_id}"
)
def get_subscriber_broker_account(
    subscriber_id: int,
    db: Session = Depends(get_db)
):

    account = (
        db.query(BrokerAccount)
        .filter(
            BrokerAccount.subscriber_id == subscriber_id
        )
        .first()
    )


    if not account:

        return {
            "status": "not_found"
        }


    return account