"""
Bethel Trading Technologies
Performance History API

Provides investor performance data from stored equity snapshots.
"""

import os

from fastapi import APIRouter, Depends, Request

from api.database import SessionLocal
from api.auth.dependency import require_admin
from api.models import EquitySnapshot
from api.services.analytics_comparison import get_analytics_comparison
from api.services.analytics_v2 import get_audited_analytics
from api.services.performance_engine import get_performance_analytics
from api.services.performance_report import get_performance_analytics as get_period_return_preview
from api.services.daily_performance import get_daily_performance
from api.services.monthly_performance import get_monthly_performance
from api.services.trade_performance import get_trade_performance


router = APIRouter(prefix="/performance", tags=["Performance History"])


def _active_master_account() -> str | None:
    configured = (os.getenv("BETHEL_MASTER_ACCOUNT") or "").strip()
    if configured:
        return configured

    db = SessionLocal()
    try:
        latest = (
            db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number.isnot(None))
            .order_by(EquitySnapshot.timestamp.desc(), EquitySnapshot.id.desc())
            .first()
        )
        return str(latest.account_number).strip() if latest and latest.account_number else None
    finally:
        db.close()


@router.get("/equity-history")
def equity_history(request: Request, _admin=Depends(require_admin)):
    db = SessionLocal()
    try:
        snapshots = db.query(EquitySnapshot).order_by(EquitySnapshot.timestamp.asc()).all()
        history = [
            {
                "id": snapshot.id,
                "account_number": snapshot.account_number,
                "balance": snapshot.balance,
                "equity": snapshot.equity,
                "profit": snapshot.profit,
                "drawdown": snapshot.drawdown,
                "timestamp": snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for snapshot in snapshots
        ]
        return {"status": "success", "count": len(history), "history": history}
    finally:
        db.close()


@router.get("/analytics")
def analytics(request: Request, _admin=Depends(require_admin)):
    """Current protected production analytics endpoint."""
    data = get_performance_analytics()
    if "consistency_score" in data:
        data["consistency_score"] = float(data["consistency_score"])
    return data


@router.get("/analytics-period-returns-preview")
def analytics_period_returns_preview(request: Request, _admin=Depends(require_admin)):
    """Read-only preview; production analytics remains unchanged."""
    data = get_period_return_preview()
    if "consistency_score" in data:
        data["consistency_score"] = float(data["consistency_score"])
    return data


@router.get("/analytics-v2")
def analytics_v2(request: Request, _admin=Depends(require_admin)):
    """Audited candidate engine for validation before any production merge."""
    account_number = _active_master_account()
    if not account_number:
        return {"status": "error", "message": "No active master account available"}
    return get_audited_analytics(account_number)


@router.get("/analytics-comparison")
def analytics_comparison(request: Request, _admin=Depends(require_admin)):
    """Read-only stable-vs-v2 comparison with data-quality and merge gates."""
    account_number = _active_master_account()
    if not account_number:
        return {"status": "error", "message": "No active master account available"}
    return get_analytics_comparison(account_number)


@router.get("/daily")
def daily_performance(request: Request, _admin=Depends(require_admin)):
    return get_daily_performance()


@router.get("/monthly")
def monthly_performance(request: Request, _admin=Depends(require_admin)):
    return get_monthly_performance()


@router.get("/trades")
def trade_performance(request: Request, _admin=Depends(require_admin)):
    return get_trade_performance()
