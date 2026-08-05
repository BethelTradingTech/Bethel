"""Research helpers for FX Blue/Myfxbook-style normalized headline returns.

This module is intentionally not wired into production analytics. It converts
an already cash-flow-neutral compounded banked return into equivalent daily,
weekly, and monthly compound rates.
"""

from __future__ import annotations


TRADING_DAYS_PER_WEEK = 5
TRADING_DAYS_PER_MONTH = 21


def normalized_compound_returns(
    *,
    banked_return_percent: float,
    trading_days: int,
) -> dict:
    """Return equivalent daily, weekly, and monthly compound rates.

    The input banked return must already be cash-flow neutral. This function
    does not derive trading performance from deposits, withdrawals, or cash P/L.
    """
    days = int(trading_days)
    total_return = float(banked_return_percent) / 100.0

    if days <= 0:
        return {
            "status": "insufficient_history",
            "reason": "nonpositive_trading_day_count",
            "daily_return_percent": None,
            "weekly_return_percent": None,
            "monthly_return_percent": None,
        }
    if total_return <= -1.0:
        return {
            "status": "invalid_return",
            "reason": "banked_return_at_or_below_total_loss",
            "daily_return_percent": None,
            "weekly_return_percent": None,
            "monthly_return_percent": None,
        }

    daily_factor = (1.0 + total_return) ** (1.0 / days)
    daily = daily_factor - 1.0
    weekly = daily_factor**TRADING_DAYS_PER_WEEK - 1.0
    monthly = daily_factor**TRADING_DAYS_PER_MONTH - 1.0

    return {
        "status": "available",
        "method": "cash_flow_neutral_banked_return_geometric_equivalent",
        "trading_days": days,
        "banked_return_percent": float(banked_return_percent),
        "daily_return_percent": daily * 100.0,
        "weekly_return_percent": weekly * 100.0,
        "monthly_return_percent": monthly * 100.0,
    }
