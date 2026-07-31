"""Subscriber copy-order execution with per-account live authorization."""

from datetime import datetime

from sqlalchemy.orm import Session

from api.broker_accounts.models import BrokerAccount
from api.copytrading import models
from api.subscription_lifecycle.service import subscriber_can_copy
from config.execution import EXECUTION_MODE, LIVE_COPY_ENABLED
from mt5_connector.orders import MT5Order


class SubscriberBridge:
    @staticmethod
    def calculate_volume(master_volume: float) -> float:
        """Subscribers receive the same lot size as the master trade."""
        return round(master_volume, 2)

    @staticmethod
    def _execution_account(db: Session, subscriber_id: int):
        return db.query(BrokerAccount).filter(
            BrokerAccount.subscriber_id == subscriber_id,
            BrokerAccount.platform == "MT5",
            BrokerAccount.status == "CONNECTED",
        ).first()

    @staticmethod
    def execute_copy_order(db: Session, copy_order):
        executed = db.query(models.CopyExecutionLog).filter(
            models.CopyExecutionLog.copy_order_id == copy_order.id,
            models.CopyExecutionLog.status == "success",
        ).first()
        if executed:
            return {
                "status": "skipped",
                "message": "Order already executed",
                "copy_order_id": copy_order.id,
            }

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

        account = SubscriberBridge._execution_account(db, subscriber.id)
        if account is None:
            return {
                "status": "blocked",
                "message": "Verified MT5 account not found",
                "copy_order_id": copy_order.id,
            }

        volume = SubscriberBridge.calculate_volume(copy_order.volume)
        mode = "PAPER"

        if EXECUTION_MODE == "LIVE" and LIVE_COPY_ENABLED:
            if not account.live_authorized or account.execution_mode != "LIVE":
                return {
                    "status": "blocked",
                    "message": "Administrator has not authorized live access for this account",
                    "copy_order_id": copy_order.id,
                }
            mode = "LIVE"
            execution_result = MT5Order(
                target_login=account.login,
                target_server=account.server,
            ).send_order(
                symbol=copy_order.symbol,
                side=copy_order.direction,
                volume=volume,
                stop_loss=copy_order.stop_loss,
                take_profit=copy_order.take_profit,
            )
        else:
            execution_result = {
                "status": "success",
                "mode": "PAPER",
                "message": "Paper execution completed",
            }

        if execution_result.get("status") == "success":
            copy_order.status = f"{mode}_EXECUTED"
            copy_order.executed_at = datetime.utcnow()
        else:
            copy_order.status = "FAILED"

        db.add(models.CopyExecutionLog(
            copy_order_id=copy_order.id,
            subscriber_id=subscriber.id,
            symbol=copy_order.symbol,
            direction=copy_order.direction,
            requested_volume=copy_order.volume,
            executed_volume=volume if execution_result.get("status") == "success" else 0.0,
            mode=mode,
            status=execution_result.get("status", "failed"),
            error_message=execution_result.get("message"),
            created_at=datetime.utcnow(),
        ))
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        return {
            "subscriber": subscriber.id,
            "account": account.login,
            "server": account.server,
            "symbol": copy_order.symbol,
            "direction": copy_order.direction,
            "volume": volume,
            "mode": mode,
            "execution": execution_result,
        }

    @staticmethod
    def process_orders(db: Session):
        orders = db.query(models.CopyOrder).filter(
            models.CopyOrder.status.in_(["PAPER", "PENDING"])
        ).all()
        results = [
            SubscriberBridge.execute_copy_order(db, order)
            for order in orders
        ]
        return {"processed": len(results), "results": results}
