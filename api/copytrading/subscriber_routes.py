"""
Bethel Trading Technologies

Copy Trading Subscriber API
"""

from fastapi import APIRouter
from api.database import SessionLocal
from api.copytrading.models import CopySubscriber
from pydantic import BaseModel


router = APIRouter(
    prefix="/copytrading/subscribers",
    tags=["Copy Subscribers"]
)



class SubscriberCreate(BaseModel):

    name: str
    email: str
    broker: str
    mt5_account: str
    mt5_account_id: int | None = None
    risk_multiplier: float = 1.0
    allocation_percent: float = 100.0



@router.post("/")
def create_subscriber(
    data: SubscriberCreate
):

    db = SessionLocal()

    try:

        subscriber = CopySubscriber(

            name=data.name,

            email=data.email,

            broker=data.broker,

            mt5_account=data.mt5_account,

            mt5_account_id=data.mt5_account_id,

            risk_multiplier=data.risk_multiplier,

            allocation_percent=data.allocation_percent

        )


        db.add(subscriber)

        db.commit()

        db.refresh(subscriber)


        return {

            "status":"success",

            "subscriber_id":subscriber.id

        }


    finally:

        db.close()





@router.get("/")
def list_subscribers():

    db = SessionLocal()

    try:

        subscribers = db.query(
            CopySubscriber
        ).all()


        return [

            {

                "id":x.id,

                "name":x.name,

                "email":x.email,

                "account":x.mt5_account,

                "risk":x.risk_multiplier,

                "allocation":x.allocation_percent,

                "status":x.status

            }

            for x in subscribers

        ]


    finally:

        db.close()

# ==========================================================
# SUBSCRIBER COPY TRADING DASHBOARD
# ==========================================================


@router.get("/{subscriber_id}/dashboard")
def subscriber_dashboard(
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

            return {

                "status": "error",

                "message": "Subscriber not found"

            }



        from api.copytrading.models import (
            CopyOrder,
            CopyExecutionLog
        )



        total_orders = db.query(
            CopyOrder
        ).filter(
            CopyOrder.subscriber_id == subscriber_id
        ).count()



        executed_orders = db.query(
            CopyOrder
        ).filter(
            CopyOrder.subscriber_id == subscriber_id,
            CopyOrder.status == "PAPER_EXECUTED"
        ).count()



        pending_orders = db.query(
            CopyOrder
        ).filter(
            CopyOrder.subscriber_id == subscriber_id,
            CopyOrder.status == "PENDING"
        ).count()



        execution_logs = db.query(
            CopyExecutionLog
        ).filter(
            CopyExecutionLog.subscriber_id == subscriber_id
        ).count()



        return {


            "status": "success",


            "subscriber": {

                "id": subscriber.id,

                "name": subscriber.name,

                "email": subscriber.email,

                "broker": subscriber.broker,

                "mt5_account": subscriber.mt5_account,

                "allocation_percent": subscriber.allocation_percent,

                "risk_multiplier": subscriber.risk_multiplier,

                "status": subscriber.status

            },


            "copy_trading": {

                "total_orders": total_orders,

                "executed_orders": executed_orders,

                "pending_orders": pending_orders,

                "execution_logs": execution_logs

            }


        }


    finally:

        db.close()