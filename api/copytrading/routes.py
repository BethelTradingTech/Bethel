"""
Bethel Trading Technologies

Copy Trading API Routes

Purpose:
    Manage copy trading workflow.

Mode:
    PAPER EXECUTION

Flow:

    Master Trade
          |
          v
    Allocation Engine
          |
          v
    Copy Orders
          |
          v
    Subscriber Bridge
          |
          v
    Copy Execution Logs


Does NOT:
    - Manage investor funds
    - Hold client assets
    - Execute external withdrawals
"""


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session


from api.database import get_db, SessionLocal

from api.copytrading import models

from api.copytrading.schemas import (
    SubscriberCreate,
    SubscriberResponse,
    MasterTradeCreate
)

from api.copytrading.service import CopyTradingService
from api.copytrading.sync_engine import TradeSyncEngine
from api.copytrading.allocation import AllocationEngine
from api.copytrading.subscriber_bridge import SubscriberBridge



router = APIRouter(
    tags=["Copy Trading"]
)



# =====================================================
# CREATE SUBSCRIBER
# =====================================================

@router.post(
    "/subscribers",
    response_model=SubscriberResponse
)
def create_subscriber(
    subscriber: SubscriberCreate,
    db: Session = Depends(get_db)
):

    new_subscriber = models.CopySubscriber(

        name=subscriber.name,

        email=subscriber.email,

        mt5_account=subscriber.account_number,

        allocation_percent=subscriber.allocation_percent,

        status="PENDING",

        payment_status="UNPAID"

    )


    db.add(new_subscriber)

    db.commit()

    db.refresh(new_subscriber)


    return new_subscriber





# =====================================================
# LIST SUBSCRIBERS
# =====================================================

@router.get(
    "/subscribers",
    response_model=list[SubscriberResponse]
)
def list_subscribers(
    db: Session = Depends(get_db)
):

    return (
        db.query(models.CopySubscriber)
        .all()
    )





# =====================================================
# RECEIVE MASTER TRADE
# =====================================================

@router.post(
    "/sync-trade"
)
def receive_master_trade(
    trade: MasterTradeCreate,
    db: Session = Depends(get_db)
):


    master_trade = models.MasterTrade(

        ticket=trade.ticket,

        symbol=trade.symbol,

        direction=trade.direction,

        volume=trade.volume,

        entry_price=trade.entry_price,

        stop_loss=trade.stop_loss,

        take_profit=trade.take_profit,

        status="OPEN"

    )


    db.add(master_trade)

    db.commit()

    db.refresh(master_trade)



    subscribers = (

        db.query(models.CopySubscriber)

        .filter(
            models.CopySubscriber.status=="ACTIVE"
        )

        .all()

    )



    created_orders=[]


    for subscriber in subscribers:

        order = CopyTradingService.create_copy_order(
            db,
            subscriber,
            master_trade
        )

        created_orders.append(order.id)



    return {

        "status":"success",

        "master_ticket":master_trade.ticket,

        "subscribers_processed":len(subscribers),

        "copy_orders_created":created_orders

    }





# =====================================================
# ALLOCATION ENGINE
# =====================================================

@router.post(
    "/sync/{master_trade_id}"
)
def sync_master_trade(
    master_trade_id:int
):

    db=SessionLocal()

    try:

        return AllocationEngine.generate_copy_orders(
            db,
            master_trade_id
        )

    finally:

        db.close()





# =====================================================
# SYNC OPEN MASTER TRADE
# =====================================================

@router.post(
    "/sync-open/{master_ticket}"
)
def sync_open_trade(
    master_ticket:int,
    db:Session=Depends(get_db)
):

    master_trade=(

        db.query(models.MasterTrade)

        .filter(
            models.MasterTrade.ticket==master_ticket
        )

        .first()

    )


    if not master_trade:

        return {

            "status":"error",

            "message":"Master trade not found"

        }



    orders=TradeSyncEngine.sync_open_trade(
        db,
        master_trade
    )


    return {

        "status":"success",

        "master_ticket":master_ticket,

        "copy_orders_created":orders

    }





# =====================================================
# PAPER EXECUTION BRIDGE
# =====================================================

@router.post(
    "/bridge-execute"
)
def bridge_execute(
    db:Session=Depends(get_db)
):

    results=SubscriberBridge.process_orders(db)


    return {

        "status":"success",

        "mode":"PAPER",

        "executed":results,

        "count":len(results)

    }





# =====================================================
# LIST COPY ORDERS
# =====================================================

@router.get(
    "/orders"
)
def list_copy_orders(
    db:Session=Depends(get_db)
):

    orders=(

        db.query(models.CopyOrder)

        .all()

    )


    return {

        "status":"success",

        "mode":"PAPER",

        "total_orders":len(orders),

        "orders":[

            {

                "id":o.id,

                "subscriber_id":o.subscriber_id,

                "subscriber_account":o.subscriber_account,

                "master_ticket":o.master_ticket,

                "symbol":o.symbol,

                "direction":o.direction,

                "volume":o.volume,

                "status":o.status,

                "created_at":o.created_at,

                "executed_at":o.executed_at

            }

            for o in orders

        ]

    }





# =====================================================
# SUBSCRIBER DETAILS
# =====================================================

@router.get(
    "/subscribers/{subscriber_id}"
)
def get_subscriber(
    subscriber_id:int,
    db:Session=Depends(get_db)
):

    subscriber=(

        db.query(models.CopySubscriber)

        .filter(
            models.CopySubscriber.id==subscriber_id
        )

        .first()

    )


    if not subscriber:

        return {

            "status":"error",

            "message":"Subscriber not found"

        }



    return {

        "status":"success",

        "subscriber":{

            "id":subscriber.id,

            "name":subscriber.name,

            "email":subscriber.email,

            "account":subscriber.mt5_account,

            "allocation_percent":subscriber.allocation_percent,

            "status":subscriber.status

        }

    }





# =====================================================
# SUBSCRIBER COPY ORDERS
# =====================================================

@router.get(
    "/subscribers/{subscriber_id}/orders"
)
def get_subscriber_orders(
    subscriber_id:int,
    db:Session=Depends(get_db)
):


    orders=(

        db.query(models.CopyOrder)

        .filter(
            models.CopyOrder.subscriber_id==subscriber_id
        )

        .all()

    )


    return {

        "status":"success",

        "subscriber_id":subscriber_id,

        "total_orders":len(orders),

        "orders":[

            {

                "id":o.id,

                "master_ticket":o.master_ticket,

                "symbol":o.symbol,

                "direction":o.direction,

                "volume":o.volume,

                "status":o.status

            }

            for o in orders

        ]

    }