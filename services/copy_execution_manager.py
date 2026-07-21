"""
Bethel Trading Technologies

Copy Execution Manager

Purpose:
    Validate and execute generated copy orders.

Modes:
    PAPER  -> Simulated execution
    LIVE   -> MT5 execution through MT5Order adapter

Safety:
    PAPER mode enabled by default.
    MT5 API execution remains disabled until intentionally enabled.
"""


import sys
import os
from datetime import datetime


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)


from api.database import SessionLocal

from api.copytrading.models import (
    CopyOrder,
    CopySubscriber
)

from mt5_connector.orders import MT5Order



class CopyExecutionManager:


    def __init__(self):

        # Safety mode
        self.paper_mode = True

        # MT5 execution adapter
        self.mt5_order = MT5Order()



    def get_pending_orders(self):

        db = SessionLocal()

        try:

            return (
                db.query(CopyOrder)
                .filter(
                    CopyOrder.status == "PAPER"
                )
                .all()
            )

        finally:

            db.close()



    def validate_subscriber(self, order):

        db = SessionLocal()

        try:

            subscriber = (
                db.query(CopySubscriber)
                .filter(
                    CopySubscriber.id == order.subscriber_id
                )
                .first()
            )


            if not subscriber:
                return False


            if subscriber.status != "ACTIVE":
                return False


            return True


        finally:

            db.close()



    def calculate_volume(self, order):

        db = SessionLocal()

        try:

            subscriber = (
                db.query(CopySubscriber)
                .filter(
                    CopySubscriber.id == order.subscriber_id
                )
                .first()
            )


            if not subscriber:
                return 0


            volume = (
                order.volume *
                subscriber.risk_multiplier
            )


            return round(volume, 2)


        finally:

            db.close()



    def execute_paper(self, order):

        db = SessionLocal()

        try:

            volume = self.calculate_volume(order)


            order.status = "EXECUTED"

            order.executed_at = datetime.utcnow()


            db.commit()


            print("\n==============================")
            print("PAPER EXECUTION SUCCESS")
            print("==============================")

            print("Copy Order:", order.id)
            print("Symbol:", order.symbol)
            print("Direction:", order.direction)
            print("Volume:", volume)
            print("Subscriber:", order.subscriber_account)
            print("Executed:", order.executed_at)

            print("==============================\n")


        finally:

            db.close()



    def execute_live(self, order):

        volume = self.calculate_volume(order)


        result = self.mt5_order.send_order(

            symbol=order.symbol,

            side=order.direction,

            volume=volume,

            stop_loss=order.stop_loss,

            take_profit=order.take_profit

        )


        return result



    def run(self):

        print(
            "Copy Execution Manager Started..."
        )


        orders = self.get_pending_orders()


        print(
            "Pending Orders:",
            len(orders)
        )


        for order in orders:


            if not self.validate_subscriber(order):

                db = SessionLocal()

                try:

                    order.status = "FAILED"

                    db.commit()

                finally:

                    db.close()


                print(
                    "Subscriber validation failed:",
                    order.id
                )

                continue



            if self.paper_mode:

                self.execute_paper(
                    order
                )


            else:

                result = self.execute_live(
                    order
                )


                print(
                    "LIVE EXECUTION RESULT:",
                    result
                )




if __name__ == "__main__":


    manager = CopyExecutionManager()

    manager.run()