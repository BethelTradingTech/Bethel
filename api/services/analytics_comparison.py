"""Read-only quality and comparison report for Analytics v2 validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal
from api.services.analytics_v2 import get_audited_analytics
from api.services.performance_engine import get_performance_analytics


def _numeric_delta(candidate: Any, stable: Any):
    if isinstance(candidate, (int, float)) and isinstance(stable, (int, float)):
        return round(float(candidate) - float(stable), 4)
    return None


def _quality_report(account_number: str) -> dict:
    db = SessionLocal()
    try:
        snapshots = (
            db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == account_number)
            .order_by(EquitySnapshot.timestamp.asc(), EquitySnapshot.id.asc())
            .all()
        )
        cash_flow_count = (
            db.query(ConnectorCashFlow)
            .filter(ConnectorCashFlow.account_number == account_number)
            .count()
        )
        deal_count = (
            db.query(ConnectorDeal)
            .filter(ConnectorDeal.account_number == account_number)
            .count()
        )

        timestamps = [item.timestamp for item in snapshots if item.timestamp is not None]
        daily_dates = sorted({stamp.date() for stamp in timestamps})
        gaps = [
            (timestamps[index] - timestamps[index - 1]).total_seconds() / 3600.0
            for index in range(1, len(timestamps))
            if timestamps[index] >= timestamps[index - 1]
        ]
        nonpositive_equity = sum(1 for item in snapshots if float(item.equity or 0) <= 0)
        negative_balance = sum(1 for item in snapshots if float(item.balance or 0) < 0)

        first_at: datetime | None = timestamps[0] if timestamps else None
        last_at: datetime | None = timestamps[-1] if timestamps else None
        coverage_days = (
            (last_at - first_at).total_seconds() / 86400.0
            if first_at is not None and last_at is not None
            else 0.0
        )
        largest_gap_hours = max(gaps) if gaps else 0.0

        issues: list[str] = []
        if len(snapshots) < 2:
            issues.append("fewer_than_two_snapshots")
        if len(daily_dates) < 2:
            issues.append("fewer_than_two_daily_observations")
        if nonpositive_equity:
            issues.append("nonpositive_equity_values")
        if negative_balance:
            issues.append("negative_balance_values")
        if largest_gap_hours > 72:
            issues.append("snapshot_gap_over_72_hours")
        if deal_count == 0:
            issues.append("no_closed_deals")

        return {
            "status": "pass" if not issues else "review_required",
            "account_number": account_number,
            "snapshot_count": len(snapshots),
            "daily_close_count": len(daily_dates),
            "cash_flow_count": cash_flow_count,
            "closed_deal_count": deal_count,
            "first_snapshot_at": first_at.isoformat() if first_at else None,
            "last_snapshot_at": last_at.isoformat() if last_at else None,
            "coverage_days": round(coverage_days, 4),
            "largest_snapshot_gap_hours": round(largest_gap_hours, 4),
            "nonpositive_equity_count": nonpositive_equity,
            "negative_balance_count": negative_balance,
            "issues": issues,
        }
    finally:
        db.close()


def get_analytics_comparison(account_number: str) -> dict:
    stable = get_performance_analytics()
    candidate = get_audited_analytics(account_number)
    returns = candidate.get("return_analytics", {})
    risk = candidate.get("risk_analytics", {})
    quality = _quality_report(account_number)

    same_account = str(stable.get("master_account")) == str(account_number)
    return {
        "status": "success" if same_account else "account_mismatch",
        "account_number": account_number,
        "same_account": same_account,
        "data_quality": quality,
        "stable_production": stable,
        "candidate_v2": candidate,
        "return_comparison": {
            "stable_total_return_percent": stable.get("total_return_percent"),
            "candidate_since_inception_return_percent": returns.get("since_inception_return_percent"),
            "since_inception_delta_percentage_points": _numeric_delta(
                returns.get("since_inception_return_percent"),
                stable.get("total_return_percent"),
            ),
            "stable_daily_return_percent": stable.get("daily_return_percent"),
            "candidate_rolling_1d_return_percent": returns.get("rolling_1d_return_percent"),
            "stable_weekly_return_percent": stable.get("weekly_return_percent"),
            "candidate_rolling_1w_return_percent": returns.get("rolling_1w_return_percent"),
            "stable_monthly_return_percent": stable.get("monthly_return_percent"),
            "candidate_rolling_1m_return_percent": returns.get("rolling_1m_return_percent"),
        },
        "risk_readiness": {
            "status": risk.get("status"),
            "required_exposed_days": risk.get("required_exposed_days", risk.get("lookback_exposed_days")),
            "available_exposed_days": risk.get("available_exposed_days"),
            "monthly_var_95_percent": risk.get("monthly_var_95_percent"),
            "monthly_expected_shortfall_95_percent": risk.get("monthly_expected_shortfall_95_percent"),
        },
        "merge_ready": bool(
            same_account
            and quality["status"] == "pass"
            and returns.get("status") == "available"
            and risk.get("status") == "available"
        ),
    }
