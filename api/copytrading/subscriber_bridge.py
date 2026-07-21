"""
Bethel Trading Technologies

Subscriber Bridge

Single Copy Trade Execution Layer

Execution Modes:
    PAPER
    LIVE
"""


from datetime import datetime

from sqlalchemy.orm import Session

from api.copytrading import models

from mt5_connector.orders import MT5Order

from config.execution import EXECUTION_MODE





class SubscriberBridge:



    # ======================================================
    # CALCULATE SUBSCRIBER VOLUME
    # ======================================================

    @staticmethod
    def calculate_volume(
        master_volume,
        subscriber
    ):


        risk_multiplier = (

            subscriber.risk_multiplier

            if subscriber.risk_multiplier

            else 1.0

        )


        allocation = (

            subscriber.allocation_percent / 100

            if subscriber.allocation_percent

            else 1.0

        )


        volume = (

            master_volume

            * risk_multiplier

            * allocation

        )


        # MT5 minimum lot

        if volume < 0.01:

            volume = 0.01


        return round(volume, 2)





    # ======================================================
    # EXECUTE SINGLE COPY ORDER
    # ======================================================

    @staticmethod
    def execute_copy_order(
        db: Session,
        copy_order
    ):


        # --------------------------------------------------
        # DUPLICATE EXECUTION PROTECTION
        # --------------------------------------------------

        existing_execution = (

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


        if existing_execution:


            return {

                "status": "skipped",

                "message": "Copy order already executed",

                "copy_order_id": copy_order.id

            }





        # --------------------------------------------------
        # LOAD SUBSCRIBER
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

                "message": "Subscriber not found",

                "copy_order_id": copy_order.id

            }





        # --------------------------------------------------
        # CALCULATE VOLUME
        # --------------------------------------------------

        volume = SubscriberBridge.calculate_volume(

            copy_order.volume,

            subscriber

        )





        execution_result = {}





        # ==================================================
        # PAPER MODE
        # ==================================================

        if EXECUTION_MODE == "PAPER":


            execution_result = {


                "status": "success",

                "mode": "PAPER",

                "message": "Paper execution completed"


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


                "status": "failed",

                "message": "Invalid execution mode"


            }





        # --------------------------------------------------
        # UPDATE COPY ORDER
        # --------------------------------------------------

        if execution_result.get("status") == "success":



            if EXECUTION_MODE == "PAPER":


                copy_order.status = "PAPER_EXECUTED"



            else:


                copy_order.status = "LIVE_EXECUTED"



            copy_order.executed_at = datetime.utcnow()




        else:


            copy_order.status = "FAILED"






        # --------------------------------------------------
        # CREATE EXECUTION LOG
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
            )


        )



        db.add(execution_log)


        db.commit()





        return {


            "subscriber": subscriber.id,


            "symbol": copy_order.symbol,


            "direction": copy_order.direction,


            "volume": volume,


            "execution": execution_result


        }





    # ======================================================
    # PROCESS ALL READY COPY ORDERS
    # ======================================================

    @staticmethod
    def process_orders(
        db: Session
    ):



        orders = (

            db.query(models.CopyOrder)

            .filter(

                models.CopyOrder.status == "PAPER"

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



        return results