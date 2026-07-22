"""
Bethel Trading Technologies

Copy Trading Service

Purpose:
    Converts master account trades into subscriber copy orders.

Rule:
    Subscriber copy order uses the exact same
    lot size as the master trade.

Mode:
    PAPER EXECUTION

This service does NOT manage investor funds.
It only creates copier instructions.
"""


from datetime import datetime

from sqlalchemy.orm import Session

from api.copytrading import models



class CopyTradingService:


    # ======================================================
    # COPY VOLUME
    # ======================================================

    @staticmethod
    def calculate_volume(
        master_volume: float
    ) -> float:
        """
        Copy exact master lot size.

        Example:

        Master:
            EURUSD BUY 0.50 lots

        Subscriber:
            EURUSD BUY 0.50 lots
        """

        return round(
            master_volume,
            2
        )



    # ======================================================
    # CREATE COPY ORDER
    # ======================================================

    @staticmethod
    def create_copy_order(
        db: Session,
        subscriber: models.CopySubscriber,
        master_trade: models.MasterTrade
    ):
        """
        Create subscriber copy order
        from master trade.
        """


        # --------------------------------------------------
        # Duplicate protection
        # --------------------------------------------------

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


        if existing:

            return existing



        # --------------------------------------------------
        # Copy exact master volume
        # --------------------------------------------------

        copied_volume = CopyTradingService.calculate_volume(

            master_trade.volume

        )



        # --------------------------------------------------
        # Create PAPER copy order
        # --------------------------------------------------

        copy_order = models.CopyOrder(

            subscriber_id=subscriber.id,

            subscriber_account=subscriber.mt5_account,

            master_ticket=master_trade.ticket,

            symbol=master_trade.symbol,

            direction=master_trade.direction,

            volume=copied_volume,

            entry_price=master_trade.entry_price,

            stop_loss=master_trade.stop_loss,

            take_profit=master_trade.take_profit,

            status="PAPER",

            created_at=datetime.utcnow()

        )


        db.add(copy_order)

        db.commit()

        db.refresh(copy_order)


        return copy_order