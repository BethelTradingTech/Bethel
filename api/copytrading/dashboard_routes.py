"""
Bethel Trading Technologies

Copy Trading Dashboard API

Provides summary statistics for:
- Subscribers
- Master Trades
- Copy Orders
- Executions

Mode:
    PAPER
"""


from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from api.database import get_db

from api.copytrading import models



router = APIRouter(

    prefix="/copytrading",

    tags=["Copy Trading Dashboard"]

)





# ==========================================================
# COPY TRADING DASHBOARD SUMMARY
# ==========================================================


@router.get("/dashboard")
def copytrading_dashboard(

    db: Session = Depends(get_db)

):


    total_subscribers = (

        db.query(
            models.CopySubscriber
        )

        .count()

    )



    active_subscribers = (

        db.query(
            models.CopySubscriber
        )

        .filter(

            models.CopySubscriber.status == "ACTIVE"

        )

        .count()

    )



    total_master_trades = (

        db.query(
            models.MasterTrade
        )

        .count()

    )



    total_copy_orders = (

        db.query(
            models.CopyOrder
        )

        .count()

    )



    pending_orders = (

        db.query(
            models.CopyOrder
        )

        .filter(

            models.CopyOrder.status == "PENDING"

        )

        .count()

    )



    executed_orders = (

        db.query(
            models.CopyOrder
        )

        .filter(

            models.CopyOrder.status == "PAPER_EXECUTED"

        )

        .count()

    )



    execution_logs = (

        db.query(
            models.CopyExecutionLog
        )

        .count()

    )



    return {


        "status": "success",


        "mode": "PAPER",


        "subscribers": {

            "total": total_subscribers,

            "active": active_subscribers

        },


        "trading": {

            "master_trades": total_master_trades,

            "copy_orders": total_copy_orders,

            "pending_orders": pending_orders,

            "executed_orders": executed_orders

        },


        "execution_logs": execution_logs

    }