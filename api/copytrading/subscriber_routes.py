"""
Bethel Trading Technologies

Subscriber Management API

Purpose:
    Provide authenticated, read-only subscriber monitoring and performance views.

Does NOT:
    - Handle payments
    - Open, modify, or close trades
    - Manage funds

Trading execution is owned exclusively by MetaTrader EAs.
"""


from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session
from api.copytrading.performance_service import sync_copy_performance
from api.copytrading.close_sync_service import sync_closed_trades

from api.database import get_db
from api.auth.dependency import require_admin, require_subscriber_or_admin

from api.copytrading.models import (
    CopySubscriber,
    CopyOrder,
    CopyExecutionLog,
    CopyTradePerformance
)


router = APIRouter(

    prefix="/copytrading/subscribers",

    tags=["Copy Subscribers"]

)



# =====================================================
# GET ALL SUBSCRIBERS
# =====================================================


@router.get("/")
def list_subscribers(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):

    subscribers = (
        db.query(
            CopySubscriber
        )
        .all()
    )


    return [

        {

            "id": subscriber.id,

            "name": subscriber.name,

            "email": subscriber.email,

            "broker": subscriber.broker,

            "mt5_account": subscriber.mt5_account,

            "allocation_percent":
                subscriber.allocation_percent,

            "risk_multiplier":
                subscriber.risk_multiplier,

            "payment_status":
                subscriber.payment_status,

            "status":
                subscriber.status

        }

        for subscriber in subscribers

    ]





# =====================================================
# GET SINGLE SUBSCRIBER
# =====================================================


@router.get("/{subscriber_id}")
def get_subscriber(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):

    subscriber = (

        db.query(
            CopySubscriber
        )

        .filter(
            CopySubscriber.id == subscriber_id
        )

        .first()

    )


    if not subscriber:

        raise HTTPException(

            status_code=404,

            detail="Subscriber not found"

        )



    return {

        "status":"success",

        "subscriber":{

            "id": subscriber.id,

            "name": subscriber.name,

            "email": subscriber.email,

            "broker": subscriber.broker,

            "mt5_account": subscriber.mt5_account,

            "payment_status":
                subscriber.payment_status,

            "status":
                subscriber.status

        }

    }





# =====================================================
# SUBSCRIBER READ-ONLY ACTIVITY DASHBOARD
# =====================================================


@router.get("/{subscriber_id}/dashboard")
def subscriber_dashboard(

    subscriber_id: int,

    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):


    subscriber = (

        db.query(
            CopySubscriber
        )

        .filter(
            CopySubscriber.id == subscriber_id
        )

        .first()

    )



    if not subscriber:

        raise HTTPException(

            status_code=404,

            detail="Subscriber not found"

        )



    total_orders = (

        db.query(
            CopyOrder
        )

        .filter(
            CopyOrder.subscriber_id ==
            subscriber_id
        )

        .count()

    )



    executed_orders = (

        db.query(
            CopyOrder
        )

        .filter(

            CopyOrder.subscriber_id ==
            subscriber_id,

            CopyOrder.status ==
            "PAPER_EXECUTED"

        )

        .count()

    )



    pending_orders = (

        db.query(
            CopyOrder
        )

        .filter(

            CopyOrder.subscriber_id ==
            subscriber_id,

            CopyOrder.status ==
            "PENDING"

        )

        .count()

    )



    execution_logs = (

        db.query(
            CopyExecutionLog
        )

        .filter(

            CopyExecutionLog.subscriber_id ==
            subscriber_id

        )

        .count()

    )



    return {


        "status":"success",


        "mode":"READ_ONLY_MONITORING",

        "platform_access":"READ_ONLY",

        "execution_owner":"METATRADER_EA",



        "subscriber":{


            "id":
                subscriber.id,


            "name":
                subscriber.name,


            "email":
                subscriber.email,


            "broker":
                subscriber.broker,


            "mt5_account":
                subscriber.mt5_account,


            "allocation_percent":
                subscriber.allocation_percent,


            "risk_multiplier":
                subscriber.risk_multiplier,


            "payment_status":
                subscriber.payment_status,


            "status":
                subscriber.status

        },



        "data_source_note":"Historical CopyOrder records are displayed as observed EA activity only; Bethel does not execute them.",

        "ea_activity":{


            "total_orders":
                total_orders,


            "observed_completed_records":
                executed_orders,


            "pending_observation_records":
                pending_orders,


            "observation_logs":
                execution_logs

        }

    }


# =====================================================
# SUBSCRIBER PERFORMANCE
# =====================================================

@router.get("/{subscriber_id}/performance")
def get_subscriber_performance(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):

    subscriber = db.query(CopySubscriber).filter(
        CopySubscriber.id == subscriber_id
    ).first()

    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="Subscriber not found"
        )


    performances = db.query(
        CopyTradePerformance
    ).filter(
        CopyTradePerformance.subscriber_id == subscriber_id
    ).all()


    total_trades = len(performances)

    open_trades = 0
    closed_trades = 0

    winning_trades = 0
    losing_trades = 0

    total_profit = 0.0
    total_loss = 0.0


    for trade in performances:

        status = (
            trade.status.upper()
            if trade.status
            else "OPEN"
        )


        if status == "OPEN":
            open_trades += 1

        else:
            closed_trades += 1


        if trade.profit_loss:

            if trade.profit_loss > 0:
                winning_trades += 1
                total_profit += trade.profit_loss

            elif trade.profit_loss < 0:
                losing_trades += 1
                total_loss += abs(trade.profit_loss)



    win_rate = 0

    if winning_trades + losing_trades > 0:
        win_rate = round(
            (
                winning_trades /
                (winning_trades + losing_trades)
            ) * 100,
            2
        )


    last_activity = None

    dates = [
        t.opened_at
        for t in performances
        if t.opened_at
    ]

    if dates:
        last_activity = max(dates).isoformat()



    return {

        "status": "success",

        "subscriber_id": subscriber_id,


        "performance": {

            "total_trades": total_trades,

            "open_trades": open_trades,

            "closed_trades": closed_trades,

            "winning_trades": winning_trades,

            "losing_trades": losing_trades,

            "win_rate_percent": win_rate,

            "total_profit": round(total_profit, 2),

            "total_loss": round(total_loss, 2)

        },


        "ea_activity": {

            "last_activity": last_activity

        },


        "synchronization_status": {

            "subscriber_status": subscriber.status,

            "synchronized": subscriber.synchronized

        }

    }


# =====================================================
# SUBSCRIBER PERFORMANCE SUMMARY
# =====================================================

@router.get("/{subscriber_id}/order-performance")
def subscriber_performance(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):

    subscriber = (
        db.query(CopySubscriber)
        .filter(
            CopySubscriber.id == subscriber_id
        )
        .first()
    )

    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="Subscriber not found"
        )

    orders = (
        db.query(CopyOrder)
        .filter(
            CopyOrder.subscriber_id == subscriber_id
        )
        .all()
    )

    total_trades = len(orders)

    pending = sum(
        1 for order in orders
        if order.status == "PENDING"
    )

    completed = sum(
        1 for order in orders
        if "EXECUTED" in order.status
    )

    failed = sum(
        1 for order in orders
        if order.status == "FAILED"
    )

    success_rate = (
        round((completed / total_trades) * 100, 2)
        if total_trades
        else 0
    )

    return {

        "status": "success",

        "subscriber": {
            "id": subscriber.id,
            "name": subscriber.name,
            "broker": subscriber.broker,
            "mt5_account": subscriber.mt5_account
        },

        "performance": {

            "total_trades": total_trades,

            "completed": completed,

            "pending": pending,

            "failed": failed,

            "success_rate": success_rate

        }

    }

# =====================================================
# HISTORICAL CLOSED-TRADE RECONCILIATION
# =====================================================

@router.post("/performance/close-sync")
def run_close_sync(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):

    return sync_closed_trades(db)



# =====================================================
# HISTORICAL PERFORMANCE RECONCILIATION
# =====================================================

@router.post("/performance/sync")
def run_performance_sync(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):

    result = sync_copy_performance(db)

    return result