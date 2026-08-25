"""Protected performance API for the dynamically resolved active master."""

from fastapi import APIRouter, Depends, Request

from api.auth.dependency import require_admin
from api.database import SessionLocal
from api.models import EquitySnapshot
from api.services.account_risk_profile import get_account_risk_profile
from api.services.analytics_comparison import get_analytics_comparison
from api.services.analytics_v2 import get_audited_analytics
from api.services.daily_performance import get_daily_performance
from api.services.fxblue_banked_return import get_fxblue_banked_return_preview
from api.services.ledger_var import get_signed_ledger_var
from api.services.master_account import resolve_active_master_account
from api.services.monthly_performance import get_monthly_performance
from api.services.normalized_return_preview import get_normalized_return_preview
from api.services.performance_engine import get_performance_analytics
from api.services.performance_report import get_performance_analytics as get_period_return_preview
from api.services.trade_performance import get_trade_performance


router = APIRouter(prefix="/performance", tags=["Performance History"])


def _active_master_account() -> str | None:
    db = SessionLocal()
    try:
        return resolve_active_master_account(db)
    finally:
        db.close()


def _round_metric(value, digits: int = 2):
    try:
        return round(float(value), digits) if value is not None else None
    except (TypeError, ValueError):
        return None


def _mask_account(value: str) -> str:
    value = str(value or "")
    return ("•" * max(0, len(value) - 4)) + value[-4:]


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
    total_factor = (1.0 + banked_return / 100.0) * (current_equity / current_balance)
    data["total_return_percent"] = round((total_factor - 1.0) * 100.0, 2)
    return data


def _apply_audited_var(data: dict) -> dict:
    """Use active-master equity VaR, with reconciled signed-ledger fallback."""
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
        risk = {"status": "error", "reason": "audited_risk_engine_unavailable"}

    if risk.get("status") != "available":
        try:
            ledger_risk = get_signed_ledger_var(account)
        except Exception:
            ledger_risk = {"status": "error", "reason": "signed_ledger_var_unavailable"}
        if ledger_risk.get("status") == "available":
            risk = ledger_risk
        else:
            equity_days = int(risk.get("available_exposed_days") or risk.get("lookback_exposed_days") or 0)
            ledger_days = int(ledger_risk.get("available_exposed_days") or 0)
            if ledger_days > equity_days:
                risk = ledger_risk

    data["var_status"] = risk.get("status", "not_available")
    data["var_reason"] = risk.get("reason")
    data["var_method"] = risk.get("method", "monthly_95_var_block_bootstrap_monte_carlo")
    data["var_source"] = risk.get("source")
    data["var_confidence_percent"] = risk.get("confidence_percent", 95)
    data["var_horizon_trading_days"] = risk.get("monthly_horizon_trading_days", 21)
    data["var_required_exposed_days"] = risk.get("required_exposed_days", 45)
    data["var_available_exposed_days"] = risk.get("available_exposed_days", risk.get("lookback_exposed_days"))
    data["var_scenario_count"] = risk.get("scenario_count", 10000)

    if risk.get("status") != "available":
        data["value_at_risk_95_percent"] = None
        data["value_at_risk_95_amount"] = None
        data["expected_shortfall_95_percent"] = None
        data["expected_shortfall_95_amount"] = None
        return data

    try:
        var_percent = float(risk["monthly_var_95_percent"])
        es_percent = float(risk["monthly_expected_shortfall_95_percent"])
        current_equity = float(data.get("current_equity") or 0.0)
    except (KeyError, TypeError, ValueError):
        data["var_status"] = "error"
        data["var_reason"] = "invalid_risk_output"
        data["value_at_risk_95_percent"] = None
        data["value_at_risk_95_amount"] = None
        data["expected_shortfall_95_percent"] = None
        data["expected_shortfall_95_amount"] = None
        return data

    data["value_at_risk_95_percent"] = round(var_percent, 2)
    data["expected_shortfall_95_percent"] = round(es_percent, 2)
    data["value_at_risk_95_amount"] = round(current_equity * var_percent / 100.0, 2) if current_equity > 0 else None
    data["expected_shortfall_95_amount"] = round(current_equity * es_percent / 100.0, 2) if current_equity > 0 else None
    return data


def _apply_account_risk_profile(data: dict) -> dict:
    """Use one active-master profile for risk, grade, and consistency."""
    if data.get("status") != "success":
        return data
    account = str(data.get("master_account") or "").strip()
    if not account:
        return data
    try:
        profile = get_account_risk_profile(account)
    except Exception:
        return data
    if profile.get("status") != "available":
        return data

    data.update({
        "risk_reward_ratio": _round_metric(profile.get("risk_reward_ratio")),
        "consistency_score": _round_metric(profile.get("consistency_score")),
        "risk_score": _round_metric(profile.get("risk_score")),
        "risk_level": profile.get("risk_level"),
        "performance_score": _round_metric(profile.get("performance_score")),
        "performance_grade": profile.get("performance_grade"),
        "volatility": _round_metric(profile.get("annualized_volatility_percent")),
        "sharpe_ratio": _round_metric(profile.get("sharpe_ratio")),
        "sortino_ratio": _round_metric(profile.get("sortino_ratio")),
        "maximum_drawdown_percent": _round_metric(profile.get("deepest_valley_percent")),
        "maximum_drawdown_amount": None,
    })
    return data


def _dashboard_values(data: dict) -> dict:
    """Return only clean user-facing values for the main Performance dashboard."""
    visible = (
        "master_account",
        "starting_capital", "funding_base", "deposits", "withdrawals",
        "current_balance", "current_equity", "floating_profit_loss",
        "closed_profit", "total_profit",
        "total_return_percent", "banked_return_percent",
        "daily_return_percent", "weekly_return_percent", "monthly_return_percent",
        "history_days",
        "profit_factor", "total_trades", "winning_trades", "losing_trades",
        "breakeven_trades", "win_rate", "gross_profit", "gross_loss",
        "average_win", "average_loss", "payoff_ratio", "expectancy",
        "recovery_factor", "maximum_drawdown_percent", "volatility", "calmar_ratio",
        "sharpe_ratio", "sortino_ratio", "risk_reward_ratio",
        "value_at_risk_95_percent", "value_at_risk_95_amount",
        "expected_shortfall_95_percent", "expected_shortfall_95_amount",
        "consistency_score", "risk_score", "risk_level",
        "performance_score", "performance_grade",
        "cash_flow_events", "snapshots_analyzed",
    )
    return {key: data[key] for key in visible if key in data and data[key] is not None}


@router.get("/public-summary")
def public_performance_summary():
    """Sanitized read-only track record for the public website and live display."""
    data = _apply_fxblue_total_return(get_performance_analytics())
    data = _apply_account_risk_profile(data)
    if not isinstance(data, dict) or data.get("status") != "success":
        return {"available": False, "read_only": True}
    account = str(data.get("master_account") or "").strip()
    if not account:
        return {"available": False, "read_only": True}

    try:
        profile = get_account_risk_profile(account)
    except Exception:
        profile = {"status": "not_available"}
    profile_available = profile.get("status") == "available"

    return {
        "available": True,
        "read_only": True,
        "verification_status": "RECONCILED" if profile_available else "PERFORMANCE DATA AVAILABLE",
        "verification_scope": "Bethel signed active-master ledger" if profile_available else "Bethel recorded active-master history",
        "account_number": _mask_account(account),
        "starting_balance": _round_metric(data.get("starting_capital")),
        "current_balance": _round_metric(data.get("current_balance")),
        "current_equity": _round_metric(data.get("current_equity")),
        "total_return_percent": _round_metric(data.get("total_return_percent")),
        "annualized_return_percent": _round_metric(profile.get("annualized_return_percent")) if profile_available else None,
        "trading_days": int(profile.get("trading_days") or data.get("history_days") or 0),
        "history_weekdays": int(profile.get("history_weekdays") or 0) if profile_available else None,
        "history_start": profile.get("history_start") if profile_available else None,
        "history_end": profile.get("history_end") if profile_available else None,
        "total_trades": int(data.get("total_trades") or 0),
        "closed_deals": int(profile.get("closed_deals") or 0) if profile_available else None,
        "win_rate": _round_metric(data.get("win_rate")),
        "maximum_drawdown_percent": _round_metric(data.get("maximum_drawdown_percent")),
        "current_drawdown_percent": _round_metric(profile.get("current_drawdown_percent")) if profile_available else None,
        "profit_factor": _round_metric(data.get("profit_factor")),
        "annualized_volatility_percent": _round_metric(profile.get("annualized_volatility_percent")) if profile_available else _round_metric(data.get("volatility")),
        "sharpe_ratio": _round_metric(profile.get("sharpe_ratio")) if profile_available else _round_metric(data.get("sharpe_ratio")),
        "sortino_ratio": _round_metric(profile.get("sortino_ratio")) if profile_available else _round_metric(data.get("sortino_ratio")),
        "consistency_score": _round_metric(profile.get("consistency_score")) if profile_available else _round_metric(data.get("consistency_score")),
        "risk_level": profile.get("risk_level") if profile_available else data.get("risk_level"),
        "performance_grade": profile.get("performance_grade") if profile_available else data.get("performance_grade"),
        "all_time_high_return_percent": _round_metric(profile.get("all_time_high_return_percent")) if profile_available else None,
        "all_time_high_date": profile.get("all_time_high_date") if profile_available else None,
        "days_since_all_time_high": int(profile.get("days_since_all_time_high") or 0) if profile_available else None,
        "worst_day_percent": _round_metric(profile.get("worst_day_percent")) if profile_available else None,
        "worst_week_percent": _round_metric(profile.get("worst_week_percent")) if profile_available else None,
        "worst_month_percent": _round_metric(profile.get("worst_month_percent")) if profile_available else None,
        "monthly_returns": profile.get("monthly_returns", []) if profile_available else [],
        "yearly_returns": profile.get("yearly_returns", []) if profile_available else [],
        "currency": data.get("currency") or "USD",
        "methodology": "Cash-flow-neutral risk statistics are reconstructed from signed active-master deals and cash flows and are published read-only only after ledger reconciliation. Total return may incorporate the configured FX Blue banked-return reconciliation when available.",
    }


@router.get("/public-history")
def public_performance_history():
    """Sanitized active-master balance/equity history for the public chart."""
    account = _active_master_account()
    if not account:
        return {"available": False, "read_only": True, "points": []}
    db = SessionLocal()
    try:
        rows = db.query(EquitySnapshot).filter(
            EquitySnapshot.account_number == account
        ).order_by(EquitySnapshot.timestamp.asc()).all()
        if not rows:
            return {"available": False, "read_only": True, "points": []}
        max_points = 120
        step = max(1, len(rows) // max_points)
        sampled = rows[::step]
        if sampled[-1].id != rows[-1].id:
            sampled.append(rows[-1])
        points = [
            {
                "timestamp": row.timestamp.isoformat() + "Z" if row.timestamp else None,
                "balance": _round_metric(row.balance),
                "equity": _round_metric(row.equity),
            }
            for row in sampled[-max_points:]
        ]
        return {"available": True, "read_only": True, "points": points}
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
    data = _apply_fxblue_total_return(get_performance_analytics())
    data = _apply_audited_var(data)
    data = _apply_account_risk_profile(data)
    return _dashboard_values(data)


@router.get("/analytics-period-returns-preview")
def analytics_period_returns_preview(request: Request, _admin=Depends(require_admin)):
    return get_period_return_preview()


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
