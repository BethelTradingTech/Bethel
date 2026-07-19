"""
Bethel Trading Technologies
Performance History API

Provides investor performance data
from stored equity snapshots.
"""


from fastapi import APIRouter, Request


from api.database import SessionLocal

from api.models import EquitySnapshot


from api.services.performance_engine import get_performance_analytics
from api.services.daily_performance import get_daily_performance
from api.services.monthly_performance import get_monthly_performance
from api.services.trade_performance import get_trade_performance





router = APIRouter(

    prefix="/performance",

    tags=["Performance History"]

)





# ==========================
# EQUITY HISTORY
# ==========================


@router.get("/equity-history")
def equity_history(

    request: Request

):



    db = SessionLocal()



    try:


        snapshots = db.query(

            EquitySnapshot

        ).order_by(

            EquitySnapshot.timestamp.asc()

        ).all()



        history = []



        for snapshot in snapshots:


            history.append({


                "id":

                snapshot.id,


                "account_number":

                snapshot.account_number,


                "balance":

                snapshot.balance,


                "equity":

                snapshot.equity,


                "profit":

                snapshot.profit,


                "drawdown":

                snapshot.drawdown,


                "timestamp":

                snapshot.timestamp.strftime(

                    "%Y-%m-%d %H:%M:%S"

                )

            })



        return {


            "status":

            "success",


            "count":

            len(history),


            "history":

            history

        }



    finally:


        db.close()

# ==========================
# PERFORMANCE ANALYTICS
# ==========================

@router.get("/analytics")
def analytics(request: Request):

    data = get_performance_analytics()

    if "consistency_score" in data:
        data["consistency_score"] = float(data["consistency_score"])

    return data


# ==========================
# DAILY PERFORMANCE ANALYTICS
# ==========================

@router.get("/daily")
def daily_performance(request: Request):

    return get_daily_performance()


# ==========================
# MONTHLY PERFORMANCE
# ==========================

@router.get("/monthly")
def monthly_performance(request: Request):

    return get_monthly_performance()


# ==========================
# TRADE PERFORMANCE ANALYTICS
# ==========================

@router.get("/trades")
def trade_performance(request: Request):

    return get_trade_performance()
