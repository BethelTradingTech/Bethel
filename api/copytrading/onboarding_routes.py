"""
Bethel Trading Technologies

Subscriber Onboarding API

Purpose:
    Handles subscriber setup before copy trading.

Does NOT:
    - Handle payments
    - Execute trades
    - Manage funds
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.database import SessionLocal
from api.copytrading.models import CopySubscriber


router = APIRouter(
    prefix="/copytrading/onboarding",
    tags=["Subscriber Onboarding"]
)


# ==============================
# MT5 CONNECTION DATA
# ==============================

class MT5ConnectionRequest(BaseModel):

    broker: str
    mt5_account: str
    mt5_account_id: int | None = None



# ==============================
# MARK SUBSCRIBER AS READY
# ==============================

@router.post("/connect-mt5/{subscriber_id}")
def connect_mt5(
    subscriber_id: int,
    data: MT5ConnectionRequest
):

    db = SessionLocal()

    try:

        subscriber = db.query(
            CopySubscriber
        ).filter(
            CopySubscriber.id == subscriber_id
        ).first()


        if not subscriber:

            raise HTTPException(
                status_code=404,
                detail="Subscriber not found"
            )


        subscriber.broker = data.broker

        subscriber.mt5_account = data.mt5_account

        subscriber.mt5_account_id = data.mt5_account_id

        subscriber.synchronized = False


        db.commit()


        return {

            "status": "success",

            "message": "MT5 account connected",

            "subscriber_id": subscriber.id

        }


    finally:

        db.close()



# ==============================
# ACTIVATE SUBSCRIBER
# ==============================

@router.post("/activate/{subscriber_id}")
def activate_subscriber(
    subscriber_id: int
):

    db = SessionLocal()

    try:

        subscriber = db.query(
            CopySubscriber
        ).filter(
            CopySubscriber.id == subscriber_id
        ).first()


        if not subscriber:

            raise HTTPException(
                status_code=404,
                detail="Subscriber not found"
            )


        if subscriber.payment_status != "PAID":

            return {

                "status": "error",

                "message": "Subscription payment required"

            }


        if not subscriber.mt5_account:

            return {

                "status": "error",

                "message": "MT5 account not connected"

            }


        subscriber.status = "ACTIVE"
        subscriber.activated_at = datetime.utcnow()


        db.commit()


        return {

            "status": "success",

            "message": "Subscriber activated",

            "subscriber_id": subscriber.id

        }


    finally:

        db.close()



# ==============================
# CHECK ONBOARDING STATUS
# ==============================

@router.get("/status/{subscriber_id}")
def onboarding_status(
    subscriber_id: int
):

    db = SessionLocal()

    try:

        subscriber = db.query(
            CopySubscriber
        ).filter(
            CopySubscriber.id == subscriber_id
        ).first()


        if not subscriber:

            raise HTTPException(
                status_code=404,
                detail="Subscriber not found"
            )


        return {

            "subscriber_id": subscriber.id,

            "name": subscriber.name,

            "status": subscriber.status,

            "payment_status": subscriber.payment_status,

            "activated_at": subscriber.activated_at.isoformat() if subscriber.activated_at else None,

            "broker": subscriber.broker,

            "mt5_account": subscriber.mt5_account,

            "synchronized": subscriber.synchronized

        }


    finally:

        db.close()



# ==============================
# CONFIRM SUBSCRIPTION PAYMENT
# ==============================

@router.post("/payment-confirm/{subscriber_id}")
def confirm_payment(
    subscriber_id: int
):

    db = SessionLocal()

    try:

        subscriber = db.query(
            CopySubscriber
        ).filter(
            CopySubscriber.id == subscriber_id
        ).first()


        if not subscriber:

            raise HTTPException(
                status_code=404,
                detail="Subscriber not found"
            )


        subscriber.payment_status = "PAID"

        db.commit()


        return {

            "status": "success",

            "message": "Payment confirmed",

            "subscriber_id": subscriber.id

        }


    finally:

        db.close()