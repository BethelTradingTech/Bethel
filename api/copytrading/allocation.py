"""
Bethel Trading Technologies

Copy Trading Allocation Engine

Purpose:
    Calculates subscriber trade volume
    from master account trades.

Formula:

copy_volume =
master_volume
*
allocation_percent / 100
*
risk_multiplier
"""


from sqlalchemy.orm import Session

from api.copytrading.models import (
    MasterTrade,
    CopySubscriber,
    CopyOrder
)

from datetime import datetime



class AllocationEngine:


    @staticmethod
    def calculate_volume(
        master_volume,
        subscriber
    ):


        volume = (

            master_volume

            *

            (
                subscriber.allocation_percent
                /
                100
            )

            *

            subscriber.risk_multiplier

        )


        # minimum MT5 volume

        if volume < 0.01:

            volume = 0.01


        return round(
            volume,
            2
        )





    @staticmethod
    def generate_copy_orders(
        db: Session,
        master_trade_id
    ):


        master = db.query(
            MasterTrade
        ).filter(

            MasterTrade.id == master_trade_id

        ).first()



        if not master:

            return {

                "status":"error",

                "message":"Master trade not found"

            }




        subscribers = db.query(
            CopySubscriber
        ).filter(

            CopySubscriber.status == "ACTIVE"

        ).all()



        created = []



        for subscriber in subscribers:


            volume = AllocationEngine.calculate_volume(

                master.volume,

                subscriber

            )



            order = CopyOrder(


                subscriber_id =
                    subscriber.id,


                subscriber_account =
                    subscriber.mt5_account,


                master_ticket =
                    master.ticket,


                symbol =
                    master.symbol,


                direction =
                    master.direction,


                volume =
                    volume,


                entry_price =
                    master.entry_price,


                stop_loss =
                    master.stop_loss,


                take_profit =
                    master.take_profit,


                status =
                    "PENDING",


                created_at =
                    datetime.utcnow()


            )


            db.add(order)


            created.append(

                {

                    "subscriber":
                        subscriber.id,

                    "volume":
                        volume

                }

            )



        db.commit()



        return {


            "status":"success",

            "orders_created":
                created

        }