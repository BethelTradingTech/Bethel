"""
Bethel Trading Technologies
Public Investor API
"""


from fastapi import APIRouter

from api.database import SessionLocal

from api.models import EquitySnapshot

from api.services.trade_performance import get_trade_performance

from api.services.monthly_performance import get_monthly_performance



router = APIRouter(

    prefix="/public/investor",

    tags=["Public Investor"]

)





@router.get("/trades")
def investor_trades():

    return get_trade_performance()





@router.get("/equity")
def investor_equity():


    db = SessionLocal()


    try:


        snapshots = db.query(
            EquitySnapshot
        ).order_by(
            EquitySnapshot.timestamp.asc()
        ).all()



        history=[]


        for s in snapshots:


            history.append({

                "equity":s.equity,

                "balance":s.balance,

                "profit":s.profit,

                "drawdown":s.drawdown,

                "timestamp":
                    s.timestamp.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

            })


        return {

            "status":"success",

            "count":len(history),

            "history":history

        }



    finally:

        db.close()






@router.get("/monthly")
def investor_monthly():

    return get_monthly_performance()