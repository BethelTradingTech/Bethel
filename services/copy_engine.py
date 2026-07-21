"""
Bethel Trading Technologies

Copy Engine

Purpose:
    Converts allocation instructions
    into subscriber copy orders.

Mode:
    PAPER EXECUTION

Features:
    - Duplicate protection
    - Allocation processing
    - Copy order tracking
"""


import os
import sys

from datetime import datetime, timezone


# =====================================================
# PROJECT PATH
# =====================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)



# =====================================================
# IMPORTS
# =====================================================

from services.allocation_engine import AllocationEngine

from api.database import SessionLocal

from api.copytrading.models import CopyOrder



# =====================================================
# COPY ENGINE
# =====================================================


class CopyEngine:


    def __init__(self):

        self.allocation_engine = AllocationEngine()

        self.paper_mode = True



    # =================================================
    # CHECK DUPLICATES
    # =================================================


    def already_exists(self, allocation):


        db = SessionLocal()


        try:

            existing = (

                db.query(CopyOrder)

                .filter(

                    CopyOrder.subscriber_id ==
                    allocation["subscriber_id"],


                    CopyOrder.master_ticket ==
                    allocation["master_ticket"]

                )

                .first()

            )


            return existing is not None



        finally:

            db.close()



    # =================================================
    # SAVE COPY ORDER
    # =================================================


    def save_copy_order(self, allocation):


        db = SessionLocal()


        try:


            if self.already_exists(allocation):


                print(

                    "SKIPPED DUPLICATE:",

                    allocation["master_ticket"]

                )

                return None



            order = CopyOrder(


                subscriber_id =
                    allocation["subscriber_id"],


                subscriber_account =
                    allocation["subscriber_account"],


                master_ticket =
                    allocation["master_ticket"],


                symbol =
                    allocation["symbol"],


                direction =
                    allocation["direction"],


                volume =
                    allocation["volume"],


                entry_price =
                    allocation["entry_price"],


                stop_loss =
                    allocation["stop_loss"],


                take_profit =
                    allocation["take_profit"],


                status="PAPER",


                created_at =
                    datetime.now(timezone.utc)

            )


            db.add(order)

            db.commit()

            db.refresh(order)



            print(

                "Saved Copy Order ID:",

                order.id

            )


            return order



        except Exception as error:


            db.rollback()


            print(

                "Database Error:",

                error

            )


            return None



        finally:

            db.close()



    # =================================================
    # PAPER EXECUTION DISPLAY
    # =================================================


    def execute_paper_order(self, allocation):


        print()

        print("=" * 40)

        print("PAPER COPY ORDER")

        print("=" * 40)



        print(
            "Subscriber:",
            allocation["subscriber_account"]
        )


        print(
            "Master Ticket:",
            allocation["master_ticket"]
        )


        print(
            "Symbol:",
            allocation["symbol"]
        )


        print(
            "Direction:",
            allocation["direction"]
        )


        print(
            "Volume:",
            allocation["volume"]
        )


        print(
            "Entry:",
            allocation["entry_price"]
        )


        print(
            "SL:",
            allocation["stop_loss"]
        )


        print(
            "TP:",
            allocation["take_profit"]
        )


        print(
            "Time:",
            datetime.now()
        )


        print("=" * 40)



        self.save_copy_order(
            allocation
        )



    # =================================================
    # RUN ENGINE
    # =================================================


    def run(self):


        print(
            "Copy Engine Started..."
        )



        allocations = (

            self.allocation_engine

            .generate_allocations()

        )



        print(

            "Allocations Found:",

            len(allocations)

        )



        for allocation in allocations:



            if self.paper_mode:


                self.execute_paper_order(
                    allocation
                )



            else:


                print(
                    "Live execution disabled"
                )





# =====================================================
# START
# =====================================================


if __name__ == "__main__":


    engine = CopyEngine()

    engine.run()