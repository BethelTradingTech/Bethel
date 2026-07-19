"""
Bethel Trading Technologies
Performance History API

Provides investor performance data
from stored equity snapshots.
"""


from fastapi import APIRouter, Request


from api.database import SessionLocal

from api.models import EquitySnapshot


from api.auth.dependency import check_auth





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


    # ==========================
    # AUTH CHECK
    # ==========================

    auth = check_auth(request)


    if auth:

        return auth



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