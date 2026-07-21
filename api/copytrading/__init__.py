"""
Bethel Trading Technologies

Copy Execution Engine

Purpose:
    Processes generated copy orders.

Mode:
    PAPER EXECUTION
"""


from sqlalchemy.orm import Session

from api.copytrading import models



class CopyExecutionEngine:


    @staticmethod
    def process_pending_orders(
        db: Session
    ):


        orders = (

            db.query(models.CopyOrder)

            .filter(
                models.CopyOrder.status == "PENDING"
            )

            .all()

        )


        processed = []


        for order in orders:


            # PAPER EXECUTION

            order.status = "PAPER"


            processed.append(

                order.id

            )


        db.commit()


        return processed