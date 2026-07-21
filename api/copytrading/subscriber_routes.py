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