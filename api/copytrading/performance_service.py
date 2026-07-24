from sqlalchemy.orm import Session

from api.copytrading.models import (
    CopyOrder,
    CopyTradePerformance
)


def sync_copy_performance(db: Session):

    copy_orders = db.query(
        CopyOrder
    ).all()


    created = 0


    for order in copy_orders:


        existing = db.query(
            CopyTradePerformance
        ).filter(
            CopyTradePerformance.copy_order_id == order.id
        ).first()


        if existing:
            continue


        performance = CopyTradePerformance(

            subscriber_id=order.subscriber_id,

            copy_order_id=order.id,

            symbol=order.symbol,

            direction=order.direction,

            entry_price=order.entry_price,

            volume=order.volume,

            status="OPEN"

        )


        db.add(performance)

        created += 1


    db.commit()


    return {
        "status": "success",
        "created_records": created
    }