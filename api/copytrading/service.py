"""
Bethel Trading Technologies

Copy Trading Service

Purpose:
    Converts master account trades into subscriber copy orders.

Mode:
    PAPER EXECUTION

This service does NOT manage investor funds.
It only creates copier instructions.
"""


from sqlalchemy.orm import Session

from api.copytrading import models



class CopyTradingService:


    # ======================================================
    # ALLOCATION CALCULATION
    # ======================================================

    @staticmethod
    def calculate_volume(
        master_volume: float,
        allocation_percent: float
    ) -> float:

        return round(
            master_volume * (allocation_percent / 100),
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


        # -----------------------------------------------
        # Duplicate protection
        # -----------------------------------------------

        existing = (
            db.query(models.CopyOrder)
            .filter(
                models.CopyOrder.master_ticket == master_trade.ticket,
                models.CopyOrder.subscriber_id == subscriber.id
            )
            .first()
        )


        if existing:

            return existing



        # -----------------------------------------------
        # Calculate copied volume
        # -----------------------------------------------

        copied_volume = CopyTradingService.calculate_volume(
            master_trade.volume,
            subscriber.allocation_percent
        )



        # -----------------------------------------------
        # Create paper copy order
        # -----------------------------------------------

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

            status="PAPER"

        )


        db.add(copy_order)

        db.commit()

        db.refresh(copy_order)


        return copy_order