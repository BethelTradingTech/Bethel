"""
Bethel Trading Technologies
MT5 Equity Snapshot Collector

Stores account performance history
for investor reporting and analytics.
"""


from datetime import datetime


from api.database import SessionLocal

from api.models import EquitySnapshot


from mt5_connector.account import MT5Account





class EquityCollector:



    def __init__(self):

        self.account = MT5Account()



    def collect(self):


        db = SessionLocal()



        try:


            # ==========================
            # GET MT5 ACCOUNT DATA
            # ==========================

            account_data = self.account.get_account_info()



            if account_data.get("status") != "connected":


                return {


                    "status": "failed",


                    "message": "MT5 account unavailable"

                }



            balance = account_data.get(

                "balance",

                0

            )


            equity = account_data.get(

                "equity",

                0

            )


            profit = account_data.get(

                "profit",

                0

            )


            account_number = account_data.get(

                "login"

            )



            # ==========================
            # CALCULATE DRAWDOWN
            # ==========================

            drawdown = 0



            if balance > 0:


                drawdown = (

                    (balance - equity)

                    /

                    balance

                ) * 100



            # ==========================
            # SAVE SNAPSHOT
            # ==========================

            snapshot = EquitySnapshot(


                account_number=str(account_number),


                balance=balance,


                equity=equity,


                profit=profit,


                drawdown=round(

                    drawdown,

                    2

                ),


                timestamp=datetime.utcnow()

            )



            db.add(snapshot)


            db.commit()


            db.refresh(snapshot)



            return {


                "status": "success",


                "message": "Equity snapshot saved",


                "snapshot_id": snapshot.id,


                "data": {


                    "balance": balance,


                    "equity": equity,


                    "profit": profit,


                    "drawdown": round(

                        drawdown,

                        2

                    )

                }

            }



        finally:


            db.close()