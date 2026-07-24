"""
Bethel Trading Technologies

Subscriber Bridge

Single Copy Trade Execution Layer

Execution Modes:
    PAPER
    LIVE

Purpose:
    Executes generated subscriber copy orders.

Responsibilities:
    - Execute copy orders
    - Prevent duplicate execution
    - Record execution logs
    - Update order status

Does NOT:
    - Manage investor funds
    - Calculate allocations
    - Apply risk multipliers
    - Generate copy orders
"""


from datetime import datetime

from sqlalchemy.orm import Session

from api.copytrading import models

from mt5_connector.orders import MT5Order

from config.execution import EXECUTION_MODE



class SubscriberBridge:


    # ======================================================
    # COPY MASTER VOLUME
    # ======================================================

    @staticmethod
    def calculate_volume(
        master_volume: float
    ) -> float:
        """
        Subscriber receives identical
        lot size as master trade.
        """

        return round(
            master_volume,
            2
        )



    # ======================================================
    # EXECUTE ONE COPY ORDER
    # ======================================================

    @staticmethod
    def execute_copy_order(
        db: Session,
        copy_order
    ):


        # --------------------------------------------------
        # Prevent duplicate execution
        # --------------------------------------------------

        executed = (

            db.query(models.CopyExecutionLog)

            .filter(

                models.CopyExecutionLog.copy_order_id
                ==
                copy_order.id,

                models.CopyExecutionLog.status
                ==
                "success"

            )

            .first()

        )


        if executed:

            return {

                "status": "skipped",

                "message":
                    "Order already executed",

                "copy_order_id":
                    copy_order.id

            }



        # --------------------------------------------------
        # Load subscriber
        # --------------------------------------------------

        subscriber = (

            db.query(models.CopySubscriber)

            .filter(

                models.CopySubscriber.id
                ==
                copy_order.subscriber_id

            )

            .first()

        )


        if not subscriber:

            return {

                "status": "failed",

                "message":
                    "Subscriber not found",

                "copy_order_id":
                    copy_order.id

            }



        # --------------------------------------------------
        # Exact master volume
        # --------------------------------------------------

        volume = SubscriberBridge.calculate_volume(

            copy_order.volume

        )



        execution_result = {}



        # ==================================================
        # PAPER MODE
        # ==================================================

        if EXECUTION_MODE == "PAPER":


            execution_result = {

                "status":
                    "success",

                "mode":
                    "PAPER",

                "message":
                    "Paper execution completed"

            }



        # ==================================================
        # LIVE MT5 MODE
        # ==================================================

        elif EXECUTION_MODE == "LIVE":


            broker = MT5Order()


            execution_result = broker.send_order(

                symbol=copy_order.symbol,

                side=copy_order.direction,

                volume=volume,

                stop_loss=copy_order.stop_loss,

                take_profit=copy_order.take_profit

            )



        # ==================================================
        # INVALID MODE
        # ==================================================

        else:


            execution_result = {

                "status":
                    "failed",

                "message":
                    "Invalid execution mode"

            }



        # --------------------------------------------------
        # Update order status
        # --------------------------------------------------

        if execution_result.get("status") == "success":


            copy_order.status = (

                "PAPER_EXECUTED"

                if EXECUTION_MODE == "PAPER"

                else

                "LIVE_EXECUTED"

            )


            copy_order.executed_at = datetime.utcnow()


        else:


            copy_order.status = "FAILED"



        # --------------------------------------------------
        # Create execution record
        # --------------------------------------------------

        execution_log = models.CopyExecutionLog(

            copy_order_id=copy_order.id,

            subscriber_id=subscriber.id,

            symbol=copy_order.symbol,

            direction=copy_order.direction,

            requested_volume=copy_order.volume,

            executed_volume=volume,

            mode=EXECUTION_MODE,

            status=execution_result.get(
                "status"
            ),

            error_message=execution_result.get(
                "message"
            ),

            created_at=datetime.utcnow()

        )


        db.add(execution_log)


        try:

            db.commit()

        except Exception:

            db.rollback()

            raise



        return {

            "subscriber":
                subscriber.id,

            "symbol":
                copy_order.symbol,

            "direction":
                copy_order.direction,

            "volume":
                volume,

            "execution":
                execution_result

        }



    # ======================================================
    # PROCESS ALL READY PAPER ORDERS
    # ======================================================

    @staticmethod
    def process_orders(
        db: Session
    ):


        orders = (

            db.query(models.CopyOrder)

            .filter(

                models.CopyOrder.status.in_(
                    [
                        "PAPER",
                        "PENDING"
                    ]
                )

            )

            .all()

        )

        results = []


        for order in orders:


            result = SubscriberBridge.execute_copy_order(

                db,

                order

            )


            results.append(result)



        return {

            "processed":
                len(results),

            "results":
                results

        }