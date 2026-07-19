"""
Bethel Trading Technologies
MT5 Snapshot Collector
"""

from datetime import datetime

from api.database import SessionLocal

from api.models import EquitySnapshot

from mt5_connector.account import MT5Account



def save_snapshot():


    db = SessionLocal()


    try:


        account = MT5Account()


        data = account.get_account_info()



        if data["status"] != "connected":

            return



        snapshot = EquitySnapshot(


            account_number=str(
                data["login"]
            ),


            balance=data["balance"],


            equity=data["equity"],


            profit=data["profit"],


            drawdown=0,


            timestamp=datetime.utcnow()

        )


        db.add(snapshot)


        db.commit()



        return {

            "status":"saved"

        }



    except Exception as e:


        db.rollback()


        return {

            "error":str(e)

        }



    finally:

        db.close()