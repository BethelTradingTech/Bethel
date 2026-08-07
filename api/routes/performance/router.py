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


def _apply_audited_var(data: dict) -> dict:
    """Promote the existing audited monthly percentage VaR into production output.

    The audited engine uses the active master's cash-flow-adjusted equity returns,
    the latest 45 exposed-market days, a 21-trading-day horizon and 10,000 block
    bootstrap Monte Carlo scenarios. The legacy trade-percentile VaR is retained
    under explicitly named legacy fields for audit compatibility, but it is no
    longer presented as the primary VaR.

    If the audited engine does not yet have enough exposed history, the primary
    VaR is deliberately unavailable rather than replaced with a guessed value.
    """
    if data.get("status") != "success":
        return data

    account = str(data.get("master_account") or "").strip()
    if not account:
        return data

    data["legacy_value_at_risk_95_percent"] = data.get("value_at_risk_95_percent")
    data["legacy_value_at_risk_95_amount"] = data.get("value_at_risk_95_amount")

    try:
        audited = get_audited_analytics(account)
        risk = audited.get("risk_analytics", {}) if isinstance(audited, dict) else {}
    except Exception as exc:
        data["var_status"] = "error"
        data["var_reason"] = "audited_risk_engine_unavailable"
        data["var_method"] = "monthly_95_var_block_bootstrap_monte_carlo"
        data["value_at_risk_95_percent"] = None
        data["value_at_risk_95_amount"] = None
        data["expected_shortfall_95_percent"] = None
        data["expected_shortfall_95_amount"] = None
        return data

    data["var_status"] = risk.get("status", "not_available")
    data["var_reason"] = risk.get("reason")
    data["var_method"] = risk.get("method", "monthly_95_var_block_bootstrap_monte_carlo")
    data["var_source"] = risk.get(
        "source",
        "signed_mt5_cash_flow_adjusted_exposed_day_equity_returns",
    )
    data["var_confidence_percent"] = risk.get("confidence_percent", 95)
    data["var_horizon_trading_days"] = risk.get("monthly_horizon_trading_days", 21)
    data["var_required_exposed_days"] = risk.get("required_exposed_days", 45)
    data["var_available_exposed_days"] = risk.get(
        "available_exposed_days",
        risk.get("lookback_exposed_days"),
    )
    data["var_scenario_count"] = risk.get("scenario_count", 10000)

    if risk.get("status") != "available":
        data["value_at_risk_95_percent"] = None
        data["value_at_risk_95_amount"] = None
        data["expected_shortfall_95_percent"] = None
        data["expected_shortfall_95_amount"] = None
        return data

    try:
        var_percent = float(risk["monthly_var_95_percent"])
        expected_shortfall_percent = float(
            risk["monthly_expected_shortfall_95_percent"]
        )
        current_equity = float(data.get("current_equity") or 0.0)
    except (KeyError, TypeError, ValueError):
        data["var_status"] = "error"
        data["var_reason"] = "invalid_audited_risk_output"
        data["value_at_risk_95_percent"] = None
        data["value_at_risk_95_amount"] = None
        data["expected_shortfall_95_percent"] = None
        data["expected_shortfall_95_amount"] = None
        return data

    data["value_at_risk_95_percent"] = round(var_percent, 2)
    data["expected_shortfall_95_percent"] = round(expected_shortfall_percent, 2)
    data["value_at_risk_95_amount"] = (
        round(current_equity * (var_percent / 100.0), 2)
        if current_equity > 0
        else None
    )
    data["expected_shortfall_95_amount"] = (
        round(current_equity * (expected_shortfall_percent / 100.0), 2)
        if current_equity > 0
        else None
    )
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
    data = _apply_audited_var(data)
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
