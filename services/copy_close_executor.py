"""
Bethel Trading Technologies

Copy Close Executor

Purpose:
    Closes subscriber copy orders
    after master trade closure.

Mode:
    PAPER EXECUTION

Flow:

MASTER TRADE CLOSED
        |
        v
READY_TO_CLOSE copy orders
        |
        v
CopyCloseExecutor
        |
        v
CLOSED copy orders
"""


import sys
import os
import time

from datetime import datetime, timezone


# ======================================================
# PROJECT ROOT
# ======================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)



# ======================================================
# INTERNAL IMPORTS
# ======================================================

from api.database import SessionLocal

from api.copytrading.models import CopyOrder




class CopyCloseExecutor:



    # ==================================================
    # PROCESS CLOSE REQUESTS
    # ==================================================

    def process_close_orders(self):


        db = SessionLocal()


        try:


            close_orders = (

                db.query(CopyOrder)

                .filter(
                    CopyOrder.status
                    ==
                    "READY_TO_CLOSE"
                )

                .all()

            )



            if not close_orders:


                return




            for order in close_orders:



                print(
                    "CLOSING COPY ORDER:",
                    order.id,
                    order.symbol
                )



                # ======================================
                # PAPER CLOSE EXECUTION
                # ======================================


                order.status = "CLOSED"


                order.executed_at = (

                    datetime.now(timezone.utc)

                )



                print(
                    "COPY ORDER CLOSED:",
                    order.id
                )



            db.commit()



        except Exception as error:



            db.rollback()


            print(
                "COPY CLOSE ERROR:",
                error
            )



        finally:


            db.close()





    # ==================================================
    # CONTINUOUS SERVICE
    # ==================================================

    def run(self):


        print(
            "Copy Close Executor Started"
        )



        while True:


            try:


                self.process_close_orders()



            except Exception as error:


                print(
                    "EXECUTOR LOOP ERROR:",
                    error
                )



            time.sleep(5)






# ======================================================
# START SERVICE
# ======================================================

if __name__ == "__main__":


    executor = CopyCloseExecutor()


    executor.run()