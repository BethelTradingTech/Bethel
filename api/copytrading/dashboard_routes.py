"""
Bethel Trading Technologies

Copy Trading Dashboard API

Provides summary statistics for the legacy copy-trading records while deriving
its displayed operating mode from the current secure Copy Hub receivers.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin
from api.copyhub.models import CopyReceiver
from api.copytrading import models
from api.database import get_db


router = APIRouter(
    prefix="/copytrading",
    tags=["Copy Trading Dashboard"],
)


def current_receiver_mode(db: Session) -> tuple[str, int, int]:
    """Return the actual receiver environment represented in the Copy Hub."""
    receivers = db.query(CopyReceiver).all()
    demo_count = sum(1 for receiver in receivers if receiver.environment == "DEMO")
    live_count = sum(
        1
        for receiver in receivers
        if receiver.environment == "LIVE" and receiver.live_authorized
    )

    if demo_count and live_count:
        mode = "MIXED"
    elif live_count:
        mode = "LIVE"
    elif demo_count:
        mode = "DEMO"
    elif receivers:
        mode = "NOT_AUTHORIZED"
    else:
        mode = "NO_RECEIVERS"

    return mode, demo_count, live_count


@router.get("/dashboard")
def copytrading_dashboard(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    total_subscribers = db.query(models.CopySubscriber).count()
    active_subscribers = (
        db.query(models.CopySubscriber)
        .filter(models.CopySubscriber.status == "ACTIVE")
        .count()
    )
    total_master_trades = db.query(models.MasterTrade).count()
    total_copy_orders = db.query(models.CopyOrder).count()
    pending_orders = (
        db.query(models.CopyOrder)
        .filter(models.CopyOrder.status == "PENDING")
        .count()
    )
    executed_orders = (
        db.query(models.CopyOrder)
        .filter(models.CopyOrder.status != "PENDING")
        .count()
    )
    execution_logs = db.query(models.CopyExecutionLog).count()
    mode, demo_receivers, live_receivers = current_receiver_mode(db)

    return {
        "status": "success",
        "mode": mode,
        "mode_source": "secure_copy_hub_receivers",
        "demo_receivers": demo_receivers,
        "live_receivers": live_receivers,
        "execution_path": "SUBSCRIBER_MT5_TERMINAL",
        "subscribers": {
            "total": total_subscribers,
            "active": active_subscribers,
        },
        "trading": {
            "master_trades": total_master_trades,
            "copy_orders": total_copy_orders,
            "pending_orders": pending_orders,
            "executed_orders": executed_orders,
        },
        "execution_logs": execution_logs,
    }
