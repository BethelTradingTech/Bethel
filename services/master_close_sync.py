"""
Bethel Trading Technologies

Master Close Synchronization

Purpose:
    Detects master trades that no longer exist in MT5.
    Marks master trade as CLOSED.
    Marks related copy orders as READY_TO_CLOSE.

Flow:

MASTER MT5
    |
    v
Missing Position Detected
    |
    v
master_trades CLOSED
    |
    v
copy_orders READY_TO_CLOSE
"""


import sys
import os
import time

from datetime import datetime, timezone


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)


from api.database import SessionLocal

from api.copytrading.models import (
    MasterTrade,
    CopyOrder
)

from mt5_connector.positions import MT5Positions



class MasterCloseSync:


    def __init__(self):

        self.positions = MT5Positions()



    def utc_now(self):

        return datetime.now(timezone.utc)



    def sync_closes(self):


        db = SessionLocal()


        try:

            mt5_data = self.positions.get_positions()


            if mt5_data["status"] != "success":

                print(
                    "MT5 ERROR:",
                    mt5_data
                )

                return



            open_tickets = [

                position["ticket"]

                for position in mt5_data["positions"]

            ]



            active_master_trades = (

                db.query(MasterTrade)

                .filter(
                    MasterTrade.status == "OPEN"
                )

                .all()

            )



            for trade in active_master_trades:



                if trade.ticket not in open_tickets:



                    trade.status = "CLOSED"

                    trade.closed_at = (
                        self.utc_now()
                    )



                    copy_orders = (

                        db.query(CopyOrder)

                        .filter(
                            CopyOrder.master_ticket
                            ==
                            trade.ticket
                        )

                        .all()

                    )



                    for order in copy_orders:


                        order.status = (
                            "READY_TO_CLOSE"
                        )



                    print(
                        "MASTER CLOSED:",
                        trade.ticket
                    )

                    print(
                        "COPY ORDERS READY:",
                        [
                            order.id
                            for order in copy_orders
                        ]
                    )



            db.commit()



        except Exception as error:


            db.rollback()


            print(
                "CLOSE SYNC ERROR:",
                error
            )



        finally:


            db.close()



    def run(self):


        print(
            "Master Close Sync Started"
        )


        while True:


            self.sync_closes()


            time.sleep(5)





if __name__ == "__main__":


    sync = MasterCloseSync()

    sync.run()