"""Signed-ledger VaR fallback for master accounts without enough equity snapshots.

This module never reconstructs historical equity. It derives cash-flow-neutral
realized daily returns from signed MT5 deal and cash-flow records, verifies that
the reconstructed ledger reconciles to the latest recorded MT5 balance, and only
then estimates monthly VaR/Expected Shortfall. The equity-based audited engine
remains preferred whenever it has enough exposed days.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import math

import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal

EXPOSURE_LOOKBACK_DAYS = 45
MONTHLY_HORIZON_TRADING_DAYS = 21
MONTE_CARLO_SCENARIOS = 10_000
BOOTSTRAP_BLOCK_DAYS = 5


def _deal_net(deal: ConnectorDeal) -> float:
    return (
        float(deal.profit or 0)
        + float(deal.commission or 0)
        + float(deal.swap or 0)
        + float(deal.fee or 0)
    )


def _rng(account_number: str) -> np.random.Generator:
    digest = hashlib.sha256(str(account_number).encode("utf-8")).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big", signed=False))


def _bootstrap(exposed_returns: np.ndarray, account_number: str) -> np.ndarray:
    count = len(exposed_returns)
    blocks_needed = math.ceil(MONTHLY_HORIZON_TRADING_DAYS / BOOTSTRAP_BLOCK_DAYS)
    rng = _rng(account_number)
    scenarios = np.empty(MONTE_CARLO_SCENARIOS, dtype=float)
    for scenario in range(MONTE_CARLO_SCENARIOS):
        path = []
        for _ in range(blocks_needed):
            start = int(rng.integers(0, count))
            for offset in range(BOOTSTRAP_BLOCK_DAYS):
                path.append(float(exposed_returns[(start + offset) % count]))
        month = np.asarray(path[:MONTHLY_HORIZON_TRADING_DAYS], dtype=float)
        scenarios[scenario] = float(np.prod(1.0 + month) - 1.0)
    return scenarios


def get_signed_ledger_var(account_number: str) -> dict:
    account_number = str(account_number or "").strip()
    if not account_number:
        return {"status": "not_available", "reason": "no_active_master_account"}

    db = SessionLocal()
    try:
        latest = (
            db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == account_number)
            .order_by(EquitySnapshot.timestamp.desc(), EquitySnapshot.id.desc())
            .first()
        )
        if latest is None:
            return {"status": "not_available", "reason": "no_current_master_snapshot"}

        deals = (
            db.query(ConnectorDeal)
            .filter(ConnectorDeal.account_number == account_number, ConnectorDeal.closed_at.isnot(None))
            .order_by(ConnectorDeal.closed_at.asc(), ConnectorDeal.id.asc())
            .all()
        )
        flows = (
            db.query(ConnectorCashFlow)
            .filter(ConnectorCashFlow.account_number == account_number, ConnectorCashFlow.occurred_at.isnot(None))
            .order_by(ConnectorCashFlow.occurred_at.asc(), ConnectorCashFlow.id.asc())
            .all()
        )
        if not deals:
            return {"status": "insufficient_history", "reason": "no_signed_closed_deals", "available_exposed_days": 0, "required_exposed_days": EXPOSURE_LOOKBACK_DAYS}

        events = []
        total_change = 0.0
        for flow in flows:
            amount = float(flow.amount or 0)
            events.append((flow.occurred_at, 0, "flow", amount, int(flow.id or 0)))
            total_change += amount
        for deal in deals:
            amount = _deal_net(deal)
            events.append((deal.closed_at, 1, "deal", amount, int(deal.id or 0)))
            total_change += amount
        events.sort(key=lambda item: (item[0], item[1], item[4]))

        current_balance = float(latest.balance or 0)
        opening_balance = current_balance - total_change
        if opening_balance <= 0:
            return {"status": "not_available", "reason": "invalid_reconstructed_opening_balance"}

        balance = opening_balance
        daily_factor = defaultdict(lambda: 1.0)
        daily_deals = defaultdict(int)
        for when, _, kind, amount, _id in events:
            if kind == "flow":
                balance += amount
                continue
            if balance <= 0:
                return {"status": "not_available", "reason": "non_positive_balance_during_ledger_reconstruction"}
            period_factor = 1.0 + (amount / balance)
            if not math.isfinite(period_factor) or period_factor <= 0:
                return {"status": "not_available", "reason": "invalid_realized_return_in_ledger"}
            daily_factor[when.date()] *= period_factor
            daily_deals[when.date()] += 1
            balance += amount

        gap = current_balance - balance
        tolerance = max(0.02, abs(current_balance) * 0.000001)
        if abs(gap) > tolerance:
            return {
                "status": "not_available",
                "reason": "signed_ledger_reconciliation_failed",
                "reconciliation_gap": round(gap, 6),
            }

        daily = np.asarray(
            [daily_factor[day] - 1.0 for day in sorted(daily_factor) if daily_deals[day] > 0],
            dtype=float,
        )
        daily = daily[np.isfinite(daily)]
        if len(daily) < EXPOSURE_LOOKBACK_DAYS:
            return {
                "status": "insufficient_history",
                "reason": "fewer_than_required_signed_ledger_exposed_days",
                "available_exposed_days": int(len(daily)),
                "required_exposed_days": EXPOSURE_LOOKBACK_DAYS,
                "source": "signed_mt5_cash_flow_neutral_realized_daily_returns",
            }

        sample = daily[-EXPOSURE_LOOKBACK_DAYS:]
        scenarios = _bootstrap(sample, account_number)
        losses = -scenarios
        var = max(0.0, float(np.percentile(losses, 95)))
        tail = losses[losses >= var]
        expected_shortfall = max(0.0, float(np.mean(tail))) if len(tail) else var
        return {
            "status": "available",
            "method": "monthly_95_var_block_bootstrap_monte_carlo_signed_ledger_fallback",
            "source": "signed_mt5_cash_flow_neutral_realized_daily_returns",
            "confidence_percent": 95,
            "lookback_exposed_days": EXPOSURE_LOOKBACK_DAYS,
            "available_exposed_days": int(len(daily)),
            "required_exposed_days": EXPOSURE_LOOKBACK_DAYS,
            "monthly_horizon_trading_days": MONTHLY_HORIZON_TRADING_DAYS,
            "scenario_count": MONTE_CARLO_SCENARIOS,
            "monthly_var_95_percent": round(var * 100.0, 4),
            "monthly_expected_shortfall_95_percent": round(expected_shortfall * 100.0, 4),
            "reconciliation_gap": round(gap, 6),
        }
    finally:
        db.close()
