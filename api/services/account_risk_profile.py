"""Unified dynamic risk/performance profile for the active master account.

Derived only from signed account deals, cash flows and the latest verified master
snapshot. No account number, expected risk label, expected grade, balance, return,
consistency score, or result is embedded here.

Balance-risk analytics use cash-flow-neutral daily realized returns across the
full weekday history window, including flat days. Consistency measures how evenly
positive daily returns are distributed rather than inheriting snapshot-frequency
statistics from another engine.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
import math
from typing import Iterable

import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class DailyReturn:
    day: object
    value: float


def _deal_net(deal: ConnectorDeal) -> float:
    return (
        float(deal.profit or 0.0)
        + float(deal.commission or 0.0)
        + float(deal.swap or 0.0)
        + float(deal.fee or 0.0)
    )


def _compound(values: Iterable[float]) -> float:
    data = np.asarray(list(values), dtype=float)
    data = data[np.isfinite(data)]
    if len(data) == 0:
        return 0.0
    if np.any(data <= -1.0):
        return -1.0
    return float(np.prod(1.0 + data) - 1.0)


def _max_drawdown_percent(values: np.ndarray) -> float:
    if len(values) == 0:
        return 0.0
    curve = np.cumprod(1.0 + values)
    peak = np.maximum.accumulate(curve)
    drawdowns = np.where(peak > 0, (curve / peak) - 1.0, 0.0)
    return abs(float(np.min(drawdowns))) * 100.0


def _group_compounded(daily: list[DailyReturn], key_fn) -> list[float]:
    grouped: dict[object, list[float]] = defaultdict(list)
    for row in daily:
        grouped[key_fn(row.day)].append(row.value)
    return [_compound(grouped[key]) for key in sorted(grouped)]


def _weekday_range(start_day, end_day):
    day = start_day
    while day <= end_day:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def _profit_distribution_consistency(values: np.ndarray) -> float:
    """Score profit distribution without embedding an expected result.

    A score near 100 means positive daily returns are spread across many days.
    The score falls when one profitable day dominates the account's total positive
    daily return. This is deliberately independent of snapshot frequency.
    """
    positive = values[np.isfinite(values) & (values > 0)]
    if len(positive) == 0:
        return 0.0
    total_positive = float(np.sum(positive))
    if total_positive <= 0:
        return 0.0
    largest_share = float(np.max(positive)) / total_positive
    return min(100.0, max(0.0, (1.0 - largest_share) * 100.0))


def _risk_label(risk_score: float) -> str:
    if risk_score < 25.0:
        return "LOW"
    if risk_score < 50.0:
        return "MODERATE"
    if risk_score < 75.0:
        return "ELEVATED"
    return "HIGH"


def _grade(score: float) -> str:
    if score >= 90.0:
        return "A+"
    if score >= 80.0:
        return "A"
    if score >= 70.0:
        return "B"
    if score >= 60.0:
        return "C"
    if score >= 50.0:
        return "D"
    return "E"


def get_account_risk_profile(account_number: str) -> dict:
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
        deals = (
            db.query(ConnectorDeal)
            .filter(
                ConnectorDeal.account_number == account_number,
                ConnectorDeal.closed_at.isnot(None),
            )
            .order_by(ConnectorDeal.closed_at.asc(), ConnectorDeal.id.asc())
            .all()
        )
        flows = (
            db.query(ConnectorCashFlow)
            .filter(
                ConnectorCashFlow.account_number == account_number,
                ConnectorCashFlow.occurred_at.isnot(None),
            )
            .order_by(ConnectorCashFlow.occurred_at.asc(), ConnectorCashFlow.id.asc())
            .all()
        )
        if latest is None or not deals:
            return {
                "status": "not_available",
                "reason": "signed_master_history_not_available",
                "master_account": account_number,
            }

        events = []
        total_change = 0.0
        for flow in flows:
            amount = float(flow.amount or 0.0)
            events.append((flow.occurred_at, 0, amount, "flow", int(flow.id or 0)))
            total_change += amount
        for deal in deals:
            amount = _deal_net(deal)
            events.append((deal.closed_at, 1, amount, "deal", int(deal.id or 0)))
            total_change += amount
        events.sort(key=lambda row: (row[0], row[1], row[4]))

        current_balance = float(latest.balance or 0.0)
        opening_balance = current_balance - total_change
        if opening_balance <= 0:
            return {
                "status": "not_available",
                "reason": "invalid_reconstructed_opening_balance",
                "master_account": account_number,
            }

        balance = opening_balance
        daily_factor = defaultdict(lambda: 1.0)
        daily_trade_count = defaultdict(int)
        for when, _, amount, kind, _id in events:
            if kind == "flow":
                balance += amount
                continue
            if balance <= 0:
                return {
                    "status": "not_available",
                    "reason": "non_positive_balance_during_reconstruction",
                    "master_account": account_number,
                }
            factor = 1.0 + (amount / balance)
            if not math.isfinite(factor) or factor <= 0:
                return {
                    "status": "not_available",
                    "reason": "invalid_signed_daily_return",
                    "master_account": account_number,
                }
            daily_factor[when.date()] *= factor
            daily_trade_count[when.date()] += 1
            balance += amount

        reconciliation_gap = current_balance - balance
        tolerance = max(0.02, abs(current_balance) * 0.000001)
        if abs(reconciliation_gap) > tolerance:
            return {
                "status": "not_available",
                "reason": "signed_ledger_reconciliation_failed",
                "master_account": account_number,
                "reconciliation_gap": round(reconciliation_gap, 6),
            }

        history_start = min(event[0].date() for event in events)
        history_end = latest.timestamp.date()
        daily = [
            DailyReturn(day=day, value=float(daily_factor[day] - 1.0))
            for day in _weekday_range(history_start, history_end)
        ]
        values = np.asarray([row.value for row in daily], dtype=float)
        values = values[np.isfinite(values)]
        if len(values) == 0:
            return {
                "status": "not_available",
                "reason": "no_valid_signed_daily_returns",
                "master_account": account_number,
            }

        mean_daily = float(np.mean(values))
        std_daily = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        negative = values[values < 0]
        downside_std = float(np.std(negative, ddof=1)) if len(negative) > 1 else 0.0

        annualized_volatility = std_daily * math.sqrt(TRADING_DAYS_PER_YEAR) * 100.0
        sharpe = (mean_daily / std_daily) * math.sqrt(TRADING_DAYS_PER_YEAR) if std_daily > 0 else 0.0
        sortino = (mean_daily / downside_std) * math.sqrt(TRADING_DAYS_PER_YEAR) if downside_std > 0 else 0.0
        deepest_valley = _max_drawdown_percent(values)

        weekly = _group_compounded(daily, lambda d: (d.isocalendar().year, d.isocalendar().week))
        monthly = _group_compounded(daily, lambda d: (d.year, d.month))
        total_return = _compound(values) * 100.0
        worst_day = float(np.min(values)) * 100.0
        worst_week = float(min(weekly)) * 100.0 if weekly else worst_day
        worst_month = float(min(monthly)) * 100.0 if monthly else worst_week
        trade_days = sum(1 for row in daily if daily_trade_count[row.day] > 0)
        consistency_score = _profit_distribution_consistency(values)

        tail_5 = abs(float(np.percentile(values, 5))) * 100.0
        raw_pressure = (
            deepest_valley
            + abs(worst_month)
            + annualized_volatility
            + tail_5
        ) / 4.0
        reward_buffer = max(0.25, 1.0 + max(sharpe, -0.75))
        risk_score = 100.0 * (1.0 - math.exp(-(raw_pressure / reward_buffer) / 20.0))
        risk_score = min(100.0, max(0.0, risk_score))

        return_component = 50.0 + 50.0 * math.tanh(total_return / 25.0)
        sharpe_component = 50.0 + 50.0 * math.tanh(sharpe / 2.0)
        risk_component = 100.0 - risk_score
        performance_score = (
            return_component * 0.30
            + sharpe_component * 0.30
            + consistency_score * 0.15
            + risk_component * 0.25
        )
        performance_score = min(100.0, max(0.0, performance_score))

        return {
            "status": "available",
            "master_account": account_number,
            "source": "signed_account_cash_flow_neutral_full_weekday_balance_returns",
            "history_start": history_start.isoformat(),
            "history_end": history_end.isoformat(),
            "history_weekdays": int(len(values)),
            "trading_days": int(trade_days),
            "closed_deals": int(len(deals)),
            "cash_flow_events": int(len(flows)),
            "reconciliation_gap": round(reconciliation_gap, 6),
            "total_realized_return_percent": round(total_return, 4),
            "annualized_volatility_percent": round(annualized_volatility, 4),
            "risk_reward_ratio": round(sharpe, 4),
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "deepest_valley_percent": round(deepest_valley, 4),
            "worst_day_percent": round(worst_day, 4),
            "worst_week_percent": round(worst_week, 4),
            "worst_month_percent": round(worst_month, 4),
            "consistency_score": round(consistency_score, 2),
            "risk_score": round(risk_score, 2),
            "risk_level": _risk_label(risk_score),
            "performance_score": round(performance_score, 2),
            "performance_grade": _grade(performance_score),
        }
    finally:
        db.close()
