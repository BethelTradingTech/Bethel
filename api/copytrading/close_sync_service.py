from datetime import datetime

from sqlalchemy.orm import Session

from api.models import Trade

from api.copytrading.models import (
    CopyOrder,
    CopyTradePerformance
)


def sync_closed_trades(db: Session):

    closed_trades = db.query(
        Trade
    ).filter(
        Trade.status == "CLOSED"
    ).all()


    updated = 0


    for trade in closed_trades:


        copy_orders = db.query(
            CopyOrder
        ).filter(
            CopyOrder.master_ticket == int(trade.ticket)
        ).all()


        for order in copy_orders:


            performance = db.query(
                CopyTradePerformance
            ).filter(
                CopyTradePerformance.copy_order_id == order.id
            ).first()


            if not performance:
                continue


            performance.exit_price = trade.exit_price

            performance.profit_loss = trade.profit


            if trade.entry_price:

                performance.profit_percent = (
                    trade.profit /
                    trade.entry_price
                ) * 100


            performance.status = "CLOSED"


            performance.closed_at = (
                trade.closed_at
                if trade.closed_at
                else datetime.utcnow()
            )


            updated += 1


    db.commit()


    return {
        "status": "success",
        "updated_records": updated
    }