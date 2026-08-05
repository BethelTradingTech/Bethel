"""Cash-flow-neutral MT5 balance returns for real calendar periods.

The engine reconstructs the balance at a requested period boundary from the
current broker balance, then compounds each closed-deal return using the
balance immediately before that deal. Deposits and withdrawals change capital
but never create performance. This follows time-weighted-return principles used
by professional account trackers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable


@dataclass(frozen=True)
class ReturnEvent:
    occurred_at: datetime
    kind: str
    amount: float


def _net_deal_profit(deal) -> float:
    return float(deal.profit or 0) + float(deal.commission or 0) + float(deal.swap or 0) + float(deal.fee or 0)


def build_events(deals: Iterable, cash_flows: Iterable, start_at: datetime) -> list[ReturnEvent]:
    events: list[ReturnEvent] = []
    for deal in deals:
        if deal.closed_at is not None and deal.closed_at >= start_at:
            events.append(ReturnEvent(deal.closed_at, "deal", _net_deal_profit(deal)))
    for flow in cash_flows:
        if flow.occurred_at is not None and flow.occurred_at >= start_at:
            events.append(ReturnEvent(flow.occurred_at, "cash_flow", float(flow.amount or 0)))
    # Cash flow is processed before a deal at the same timestamp, matching the
    # broker balance available to the subsequently booked deal.
    events.sort(key=lambda item: (item.occurred_at, 0 if item.kind == "cash_flow" else 1))
    return events


def rolling_balance_twr(
    *,
    current_balance: float,
    deals: Iterable,
    cash_flows: Iterable,
    end_at: datetime,
    period_days: float,
) -> dict:
    """Return actual period TWR, not an annualised full-history estimate."""
    start_at = end_at - timedelta(days=period_days)
    events = build_events(deals, cash_flows, start_at)
    total_after_start = sum(event.amount for event in events)
    opening_balance = float(current_balance) - total_after_start

    if opening_balance <= 0:
        return {
            "status": "insufficient_history",
            "reason": "nonpositive_reconstructed_opening_balance",
            "start_at": start_at,
            "end_at": end_at,
            "return_percent": None,
            "deal_count": 0,
            "cash_flow_count": 0,
        }

    balance = opening_balance
    growth = 1.0
    deal_count = 0
    cash_flow_count = 0
    for event in events:
        if event.kind == "cash_flow":
            balance += event.amount
            cash_flow_count += 1
            if balance <= 0:
                return {
                    "status": "insufficient_history",
                    "reason": "nonpositive_balance_after_cash_flow",
                    "start_at": start_at,
                    "end_at": end_at,
                    "return_percent": None,
                    "deal_count": deal_count,
                    "cash_flow_count": cash_flow_count,
                }
            continue

        if balance <= 0:
            return {
                "status": "insufficient_history",
                "reason": "nonpositive_balance_before_deal",
                "start_at": start_at,
                "end_at": end_at,
                "return_percent": None,
                "deal_count": deal_count,
                "cash_flow_count": cash_flow_count,
            }
        factor = 1.0 + (event.amount / balance)
        if factor <= 0:
            return {
                "status": "insufficient_history",
                "reason": "account_loss_reached_or_exceeded_100_percent",
                "start_at": start_at,
                "end_at": end_at,
                "return_percent": None,
                "deal_count": deal_count,
                "cash_flow_count": cash_flow_count,
            }
        growth *= factor
        balance += event.amount
        deal_count += 1

    return {
        "status": "available",
        "method": "cash_flow_neutral_closed_deal_time_weighted_return",
        "start_at": start_at,
        "end_at": end_at,
        "opening_balance": opening_balance,
        "closing_balance": float(current_balance),
        "return_percent": (growth - 1.0) * 100.0,
        "deal_count": deal_count,
        "cash_flow_count": cash_flow_count,
    }
