"""Read-only subscriber monitoring bridge.

Bethel records master/subscriber synchronization state but never places,
modifies, or closes a broker order. Authorized EAs inside MetaTrader manage
all execution.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from api.copytrading import models
from api.subscription_lifecycle.service import subscriber_can_copy


class SubscriberBridge:
    @staticmethod
    def calculate_volume(master_volume: float) -> float:
        """Display the master volume for monitoring; never submit it to a broker."""
        return round(master_volume, 2)

    @staticmethod
    def execute_copy_order(db: Session, copy_order):
        existing = db.query(models.CopyExecutionLog).filter(
            models.CopyExecutionLog.copy_order_id == copy_order.id,
            models.CopyExecutionLog.status == "monitored",
        ).first()
        if existing:
            return {"status": "skipped", "reason": "already_monitored"}

        subscriber = db.query(models.CopySubscriber).filter(
            models.CopySubscriber.id == copy_order.subscriber_id
        ).first()
        if subscriber is None:
            return {
                "status": "failed",
                "message": "Subscriber not found",
                "copy_order_id": copy_order.id,
            }
        if not subscriber_can_copy(db, subscriber.id):
            return {
                "status": "blocked",
                "message": "Subscriber activation requirements are not complete",
                "copy_order_id": copy_order.id,
            }

        monitored_volume = SubscriberBridge.calculate_volume(copy_order.volume)
        copy_order.status = "EA_MANAGED"
        copy_order.executed_at = None
        db.add(models.CopyExecutionLog(
            copy_order_id=copy_order.id,
            subscriber_id=subscriber.id,
            symbol=copy_order.symbol,
            direction=copy_order.direction,
            requested_volume=copy_order.volume,
            executed_volume=0.0,
            mode="EA_MANAGED",
            status="monitored",
            error_message="No broker order sent; execution is managed by MT4/MT5 EAs",
            created_at=datetime.utcnow(),
        ))
        db.commit()
        return {
            "status": "monitored",
            "subscriber": subscriber.id,
            "symbol": copy_order.symbol,
            "direction": copy_order.direction,
            "display_volume": monitored_volume,
            "executed_volume": 0.0,
            "mode": "EA_MANAGED",
            "message": "No broker order sent by Bethel",
        }

    @staticmethod
    def process_orders(db: Session):
        orders = db.query(models.CopyOrder).filter(
            models.CopyOrder.status.in_(["PAPER", "PENDING"])
        ).all()
        results = [SubscriberBridge.execute_copy_order(db, order) for order in orders]
        return {"processed": len(results), "results": results, "mode": "EA_MANAGED"}
