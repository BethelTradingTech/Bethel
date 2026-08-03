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


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, inspect, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


from api.database import Base, get_db, SessionLocal
from api.auth.dependency import require_admin, require_subscriber_or_admin, require_super_admin

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
from api.subscription_lifecycle.service import sweep_subscriptions
from config.execution import EXECUTION_MODE



router = APIRouter(
    tags=["Copy Trading"]
)


class PermanentDeleteSubscriberRequest(BaseModel):
    confirmation: str = Field(min_length=10, max_length=200)



# =====================================================
# CREATE SUBSCRIBER
# =====================================================

@router.post(
    "/subscribers",
    response_model=SubscriberResponse
)
def create_subscriber(
    subscriber: SubscriberCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    email = subscriber.email.strip().lower()
    account_number = subscriber.account_number.strip()
    matches = db.query(models.CopySubscriber).filter(or_(
        func.lower(models.CopySubscriber.email) == email,
        models.CopySubscriber.mt5_account == account_number,
    )).all()
    if len({row.id for row in matches}) > 1:
        raise HTTPException(
            status_code=409,
            detail="The email and trading account belong to different subscribers",
        )

    record = matches[0] if matches else models.CopySubscriber(
        name=subscriber.name.strip(),
        email=email,
        mt5_account=account_number,
        allocation_percent=subscriber.allocation_percent,
        status="PENDING",
        payment_status="UNPAID",
    )
    if not matches:
        db.add(record)
    else:
        record.name = subscriber.name.strip()
        record.email = email
        record.mt5_account = account_number
        record.allocation_percent = subscriber.allocation_percent

    try:
        db.commit()
        db.refresh(record)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This email address or MT5 account is already registered",
        ) from exc
    return record





# =====================================================
# LIST SUBSCRIBERS
# =====================================================

@router.get(
    "/subscribers",
    response_model=list[SubscriberResponse]
)
def list_subscribers(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):

    return (
        db.query(models.CopySubscriber)
        .all()
    )


@router.delete("/subscribers/{subscriber_id}")
def permanently_delete_pending_subscriber(
    subscriber_id: int,
    data: PermanentDeleteSubscriberRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    subscriber = db.query(models.CopySubscriber).filter(
        models.CopySubscriber.id == subscriber_id
    ).first()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    expected = f"DELETE SUBSCRIBER {subscriber_id}"
    if data.confirmation != expected:
        raise HTTPException(status_code=422, detail=f"Confirmation must be: {expected}")
    if subscriber.status == "ACTIVE" or subscriber.payment_status == "PAID" or subscriber.activated_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Active or paid subscribers cannot be permanently deleted",
        )

    # Delete dependent onboarding/test records in reverse dependency order.
    # This operation is intentionally restricted to never-activated, unpaid records.
    existing_tables = set(inspect(db.get_bind()).get_table_names())
    for table in reversed(Base.metadata.sorted_tables):
        if table.name == models.CopySubscriber.__tablename__:
            continue
        if table.name in existing_tables and "subscriber_id" in table.c:
            db.execute(delete(table).where(table.c.subscriber_id == subscriber_id))
    db.delete(subscriber)
    db.commit()
    return {"status": "deleted", "subscriber_id": subscriber_id}





# =====================================================
# RECEIVE MASTER TRADE
# =====================================================

@router.post(
    "/sync-trade"
)
def receive_master_trade(
    trade: MasterTradeCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
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



    sweep_subscriptions(db)

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
    master_trade_id:int,
    _admin=Depends(require_admin),
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
    db:Session=Depends(get_db),
    _admin=Depends(require_admin),
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
    db:Session=Depends(get_db),
    _admin=Depends(require_admin),
):
    results=SubscriberBridge.process_orders(db)
    return {
        "status": "success",
        "mode": EXECUTION_MODE,
        **results,
    }





# =====================================================
# LIST COPY ORDERS
# =====================================================

@router.get(
    "/orders"
)
def list_copy_orders(
    db:Session=Depends(get_db),
    _admin=Depends(require_admin),
):

    orders=(

        db.query(models.CopyOrder)

        .all()

    )


    return {

        "status":"success",

        "mode":EXECUTION_MODE,

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
    "/subscribers/{subscriber_id}/profile"
)
def get_subscriber(
    subscriber_id:int,
    db:Session=Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
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
    db:Session=Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
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
