"""Production performance report with authentic rolling MT5 returns."""

from __future__ import annotations

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal
from api.services.performance_engine import get_performance_analytics as get_legacy_report
from api.services.period_returns import rolling_balance_twr


def _period_value(report: dict) -> float | None:
    value = report.get("return_percent")
    return round(float(value), 2) if value is not None else None


def get_performance_analytics() -> dict:
    """Preserve the complete table and replace only the three faulty returns."""
    report = get_legacy_report()
    if report.get("status") != "success":
        return report

    account = str(report.get("master_account") or "").strip()
    db = SessionLocal()
    try:
        latest = (
            db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == account)
            .order_by(EquitySnapshot.timestamp.desc(), EquitySnapshot.id.desc())
            .first()
        )
        if latest is None or latest.timestamp is None:
            report.update({
                "daily_return_percent": None,
                "weekly_return_percent": None,
                "monthly_return_percent": None,
                "period_return_status": "insufficient_history",
                "period_return_reason": "no_current_account_snapshot",
            })
            return report

        deals = (
            db.query(ConnectorDeal)
            .filter(ConnectorDeal.account_number == account)
            .order_by(ConnectorDeal.closed_at.asc(), ConnectorDeal.id.asc())
            .all()
        )
        flows = (
            db.query(ConnectorCashFlow)
            .filter(ConnectorCashFlow.account_number == account)
            .order_by(ConnectorCashFlow.occurred_at.asc(), ConnectorCashFlow.id.asc())
            .all()
        )
        current_balance = float(latest.balance or report.get("current_balance") or 0)
        periods = {
            "daily": rolling_balance_twr(
                current_balance=current_balance,
                deals=deals,
                cash_flows=flows,
                end_at=latest.timestamp,
                period_days=1,
            ),
            "weekly": rolling_balance_twr(
                current_balance=current_balance,
                deals=deals,
                cash_flows=flows,
                end_at=latest.timestamp,
                period_days=7,
            ),
            "monthly": rolling_balance_twr(
                current_balance=current_balance,
                deals=deals,
                cash_flows=flows,
                end_at=latest.timestamp,
                period_days=30,
            ),
        }
        report["daily_return_percent"] = _period_value(periods["daily"])
        report["weekly_return_percent"] = _period_value(periods["weekly"])
        report["monthly_return_percent"] = _period_value(periods["monthly"])
        report["period_return_method"] = "cash_flow_neutral_closed_deal_time_weighted_return"
        report["period_return_source"] = "signed_mt5_deals_cash_flows_and_current_balance"
        report["period_return_windows"] = {
            name: {
                "status": value.get("status"),
                "start_at": value.get("start_at").isoformat() if value.get("start_at") else None,
                "end_at": value.get("end_at").isoformat() if value.get("end_at") else None,
                "deal_count": value.get("deal_count"),
                "cash_flow_count": value.get("cash_flow_count"),
                "reason": value.get("reason"),
            }
            for name, value in periods.items()
        }
        report["period_return_status"] = (
            "available"
            if all(item.get("status") == "available" for item in periods.values())
            else "partial"
        )
        return report
    finally:
        db.close()
