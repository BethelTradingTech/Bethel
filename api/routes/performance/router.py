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
from api.services.normalized_return_preview import get_normalized_return_preview
from api.services.fxblue_banked_return import get_fxblue_banked_return_preview
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


def _apply_fxblue_total_return(data: dict) -> dict:
    """Replace only total_return_percent with the FX Blue-style headline total.

    Banked return is the geometrically linked, cash-flow-neutral balance return.
    FX Blue's headline total also reflects current floating P/L. Applying the
    current equity/balance factor to the banked growth factor gives that total:

        total_factor = banked_growth_factor * (current_equity / current_balance)

    Everything is read from the currently active master account. No account
    number, funding amount, balance, equity, or expected percentage is fixed in
    code. If the audit is unavailable or does not belong to the same master,
    the stable total-return value is left unchanged rather than guessed.
    """
    if data.get("status") != "success":
        return data

    account = str(data.get("master_account") or "").strip()
    if not account:
        return data

    audit = get_fxblue_banked_return_preview()
    if audit.get("status") != "available":
        return data
    if str(audit.get("master_account") or "").strip() != account:
        return data

    try:
        banked_return = float(audit["banked_return_percent"])
        current_balance = float(data["current_balance"])
        current_equity = float(data["current_equity"])
    except (KeyError, TypeError, ValueError):
        return data

    if current_balance <= 0 or banked_return <= -100.0:
        return data

    banked_growth_factor = 1.0 + (banked_return / 100.0)
    equity_balance_factor = current_equity / current_balance
    total_return_percent = (
        (banked_growth_factor * equity_balance_factor) - 1.0
    ) * 100.0

    data["total_return_percent"] = round(total_return_percent, 2)
    return data


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
    data = _apply_fxblue_total_return(get_performance_analytics())
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


@router.get("/analytics-normalized-returns-preview")
def analytics_normalized_returns_preview(request: Request, _admin=Depends(require_admin)):
    """Read-only FX Blue/Myfxbook-style normalized headline-return preview."""
    return get_normalized_return_preview()


@router.get("/analytics-fxblue-banked-return-preview")
def analytics_fxblue_banked_return_preview(request: Request, _admin=Depends(require_admin)):
    """Read-only cash-flow-subperiod banked return audit."""
    return get_fxblue_banked_return_preview()


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
