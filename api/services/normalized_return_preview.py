"""Read-only FX Blue/Myfxbook-style normalized return preview.

This service deliberately does not replace production analytics fields. It
converts the existing cash-flow-neutral banked return into equivalent average
daily, weekly, and monthly compound rates using elapsed Monday-Friday trading
days across the verified account history.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal
from api.services.normalized_returns import normalized_compound_returns
from api.services.performance_engine import get_performance_analytics


def count_weekdays_inclusive(start_at: datetime, end_at: datetime) -> int:
    """Count Monday-Friday dates inclusively between two timestamps."""
    start_day: date = start_at.date()
    end_day: date = end_at.date()
    if end_day < start_day:
        return 0

    count = 0
    current = start_day
    while current <= end_day:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def _earliest_account_event(db, account: str) -> datetime | None:
    earliest_deal = (
        db.query(ConnectorDeal)
        .filter(ConnectorDeal.account_number == account)
        .filter(ConnectorDeal.closed_at.isnot(None))
        .order_by(ConnectorDeal.closed_at.asc(), ConnectorDeal.id.asc())
        .first()
    )
    earliest_flow = (
        db.query(ConnectorCashFlow)
        .filter(ConnectorCashFlow.account_number == account)
        .filter(ConnectorCashFlow.occurred_at.isnot(None))
        .order_by(ConnectorCashFlow.occurred_at.asc(), ConnectorCashFlow.id.asc())
        .first()
    )

    candidates = []
    if earliest_deal and earliest_deal.closed_at:
        candidates.append(earliest_deal.closed_at)
    if earliest_flow and earliest_flow.occurred_at:
        candidates.append(earliest_flow.occurred_at)
    return min(candidates) if candidates else None


def get_normalized_return_preview() -> dict:
    """Return a read-only normalized headline-return comparison payload."""
    stable = get_performance_analytics()
    if stable.get("status") != "success":
        return stable

    account = str(stable.get("master_account") or "").strip()
    if not account:
        return {"status": "error", "message": "No active master account available"}

    banked_return = stable.get("banked_return_percent")
    if banked_return is None:
        return {
            "status": "insufficient_history",
            "master_account": account,
            "reason": "banked_return_unavailable",
        }

    db = SessionLocal()
    try:
        latest = (
            db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == account)
            .filter(EquitySnapshot.timestamp.isnot(None))
            .order_by(EquitySnapshot.timestamp.desc(), EquitySnapshot.id.desc())
            .first()
        )
        earliest = _earliest_account_event(db, account)

        if latest is None or latest.timestamp is None or earliest is None:
            return {
                "status": "insufficient_history",
                "master_account": account,
                "reason": "account_history_boundaries_unavailable",
            }

        trading_days = count_weekdays_inclusive(earliest, latest.timestamp)
        normalized = normalized_compound_returns(
            banked_return_percent=float(banked_return),
            trading_days=trading_days,
        )

        return {
            "status": normalized.get("status"),
            "master_account": account,
            "preview_only": True,
            "production_analytics_unchanged": True,
            "method": normalized.get("method"),
            "source": "stable_cash_flow_neutral_banked_return_and_verified_account_history",
            "history_start": earliest.isoformat(),
            "history_end": latest.timestamp.isoformat(),
            "calendar_history_days": (latest.timestamp - earliest).total_seconds() / 86400.0,
            "elapsed_trading_weekdays": trading_days,
            "banked_return_percent": float(banked_return),
            "average_daily_return_percent": normalized.get("daily_return_percent"),
            "average_weekly_return_percent": normalized.get("weekly_return_percent"),
            "average_monthly_return_percent": normalized.get("monthly_return_percent"),
            "display_rounded": {
                "average_daily_return_percent": (
                    round(float(normalized["daily_return_percent"]), 2)
                    if normalized.get("daily_return_percent") is not None
                    else None
                ),
                "average_weekly_return_percent": (
                    round(float(normalized["weekly_return_percent"]), 2)
                    if normalized.get("weekly_return_percent") is not None
                    else None
                ),
                "average_monthly_return_percent": (
                    round(float(normalized["monthly_return_percent"]), 2)
                    if normalized.get("monthly_return_percent") is not None
                    else None
                ),
            },
            "reason": normalized.get("reason"),
            "definition": (
                "Equivalent compound-average headline returns; these are not "
                "actual rolling or calendar-period returns."
            ),
        }
    finally:
        db.close()
