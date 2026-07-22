"""
Bethel Trading Technologies

Trade Synchronization Engine

Purpose:
    Keeps subscriber copy orders synchronized
    with master account trades.

Rule:
    Subscriber receives the exact same lot size
    as the master trade.

Mode:
    PAPER EXECUTION
"""


from sqlalchemy.orm import Session

from datetime import datetime

from api.copytrading import models




class TradeSyncEngine:



    # ======================================================
    # SYNC OPEN MASTER TRADE
    # ======================================================

    @staticmethod
    def sync_open_trade(
        db: Session,
        master_trade
    ):


        subscribers = (

            db.query(models.CopySubscriber)

            .filter(
                models.CopySubscriber.status == "ACTIVE"
            )

            .all()

        )



        created = []



        for subscriber in subscribers:



            existing = (

                db.query(models.CopyOrder)

                .filter(

                    models.CopyOrder.master_ticket
                    ==
                    master_trade.ticket,

                    models.CopyOrder.subscriber_id
                    ==
                    subscriber.id

                )

                .first()

            )



            # Duplicate protection

            if existing:

                continue





            # IMPORTANT:
            # COPY EXACT MASTER LOT SIZE

            volume = round(
                master_trade.volume,
                2
            )





            order = models.CopyOrder(


                subscriber_id=subscriber.id,


                subscriber_account=subscriber.mt5_account,


                master_ticket=master_trade.ticket,


                symbol=master_trade.symbol,


                direction=master_trade.direction,


                volume=volume,


                entry_price=master_trade.entry_price,


                stop_loss=master_trade.stop_loss,


                take_profit=master_trade.take_profit,


                status="PENDING",


                created_at=datetime.utcnow()


            )



            db.add(order)


            db.commit()


            db.refresh(order)



            created.append(order.id)



        return created





    # ======================================================
    # SYNC CLOSED MASTER TRADE
    # ======================================================

    @staticmethod
    def sync_close_trade(
        db: Session,
        master_ticket: int
    ):



        orders = (

            db.query(models.CopyOrder)

            .filter(

                models.CopyOrder.master_ticket
                ==
                master_ticket

            )

            .all()

        )



        closed = []



        for order in orders:


            order.status = "CLOSED"


            order.executed_at = datetime.utcnow()


            closed.append(order.id)



        db.commit()



        return closed