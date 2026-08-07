"""
Bethel Trading Technologies
Performance History API

Provides protected performance data from the currently active master account.
"""

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
from api.services.master_account import resolve_active_master_account


router = APIRouter(prefix="/performance", tags=["Performance History"])


def _active_master_account() -> str | None:
    db = SessionLocal()
    try:
        return resolve_active_master_account(db)
    finally:
        db.close()


def _apply_fxblue_total_return(data: dict) -> dict:
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
    data["total_return_percent"] = round(((banked_growth_factor * equity_balance_factor) - 1.0) * 100.0, 2)
    return data


def _apply_audited_var(data: dict) -> dict:
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
    except Exception:
        data.update({
            "var_status": "error",
            "var_reason": "audited_risk_engine_unavailable",
            "var_method": "monthly_95_var_block_bootstrap_monte_carlo",
            "value_at_risk_95_percent": None,
            "value_at_risk_95_amount": None,
            "expected_shortfall_95_percent": None,
            "expected_shortfall_95_amount": None,
        })
        return data

    data["var_status"] = risk.get("status", "not_available")
    data["var_reason"] = risk.get("reason")
    data["var_method"] = risk.get("method", "monthly_95_var_block_bootstrap_monte_carlo")
    data["var_source"] = risk.get("source", "signed_mt5_cash_flow_adjusted_exposed_day_equity_returns")
    data["var_confidence_percent"] = risk.get("confidence_percent", 95)
    data["var_horizon_trading_days"] = risk.get("monthly_horizon_trading_days", 21)
    data["var_required_exposed_days"] = risk.get("required_exposed_days", 45)
    data["var_available_exposed_days"] = risk.get("available_exposed_days", risk.get("lookback_exposed_days"))
    data["var_scenario_count"] = risk.get("scenario_count", 10000)

    if risk.get("status") != "available":
        data.update({
            "value_at_risk_95_percent": None,
            "value_at_risk_95_amount": None,
            "expected_shortfall_95_percent": None,
            "expected_shortfall_95_amount": None,
        })
        return data

    try:
        var_percent = float(risk["monthly_var_95_percent"])
        expected_shortfall_percent = float(risk["monthly_expected_shortfall_95_percent"])
        current_equity = float(data.get("current_equity") or 0.0)
    except (KeyError, TypeError, ValueError):
        data.update({
            "var_status": "error",
            "var_reason": "invalid_audited_risk_output",
            "value_at_risk_95_percent": None,
            "value_at_risk_95_amount": None,
            "expected_shortfall_95_percent": None,
            "expected_shortfall_95_amount": None,
        })
        return data

    data["value_at_risk_95_percent"] = round(var_percent, 2)
    data["expected_shortfall_95_percent"] = round(expected_shortfall_percent, 2)
    data["value_at_risk_95_amount"] = round(current_equity * (var_percent / 100.0), 2) if current_equity > 0 else None
    data["expected_shortfall_95_amount"] = round(current_equity * (expected_shortfall_percent / 100.0), 2) if current_equity > 0 else None
    return data


def _prioritize_dashboard_analytics(data: dict) -> dict:
    priority = (
        "status", "master_account", "total_return_percent", "banked_return_percent",
        "daily_return_percent", "weekly_return_percent", "monthly_return_percent",
        "value_at_risk_95_percent", "expected_shortfall_95_percent", "var_status",
        "var_confidence_percent", "var_horizon_trading_days", "var_available_exposed_days",
        "var_required_exposed_days", "var_scenario_count", "maximum_drawdown_percent",
        "volatility", "sharpe_ratio", "sortino_ratio", "risk_level",
    )
    ordered = {key: data[key] for key in priority if key in data}
    ordered.update(data)
    return ordered


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
    data = _apply_fxblue_total_return(get_performance_analytics())
    data = _apply_audited_var(data)
    if "consistency_score" in data:
        data["consistency_score"] = float(data["consistency_score"])
    return _prioritize_dashboard_analytics(data)


@router.get("/analytics-period-returns-preview")
def analytics_period_returns_preview(request: Request, _admin=Depends(require_admin)):
    data = get_period_return_preview()
    if "consistency_score" in data:
        data["consistency_score"] = float(data["consistency_score"])
    return data


@router.get("/analytics-normalized-returns-preview")
def analytics_normalized_returns_preview(request: Request, _admin=Depends(require_admin)):
    return get_normalized_return_preview()


@router.get("/analytics-fxblue-banked-return-preview")
def analytics_fxblue_banked_return_preview(request: Request, _admin=Depends(require_admin)):
    return get_fxblue_banked_return_preview()


@router.get("/analytics-v2")
def analytics_v2(request: Request, _admin=Depends(require_admin)):
    account_number = _active_master_account()
    if not account_number:
        return {"status": "error", "message": "No active master account available"}
    return get_audited_analytics(account_number)


@router.get("/analytics-comparison")
def analytics_comparison(request: Request, _admin=Depends(require_admin)):
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
