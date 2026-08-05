"""Auditable FX Blue-style cash-flow-neutral banked return preview.

External cash flows split the account history into subperiods. Trading growth
within each subperiod is measured against the capital available immediately
after the preceding cash flow, and the subperiod factors are geometrically
linked. Production analytics are not changed by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal
from api.services.performance_engine import get_performance_analytics


@dataclass(frozen=True)
class LedgerEvent:
    occurred_at: datetime
    kind: str
    amount: float
    source_id: int | None = None


def _deal_net(deal) -> float:
    return (
        float(deal.profit or 0.0)
        + float(deal.commission or 0.0)
        + float(deal.swap or 0.0)
        + float(deal.fee or 0.0)
    )


def build_ledger_events(deals: Iterable, cash_flows: Iterable) -> list[LedgerEvent]:
    events: list[LedgerEvent] = []
    for deal in deals:
        if deal.closed_at is not None:
            events.append(LedgerEvent(deal.closed_at, "deal", _deal_net(deal), getattr(deal, "id", None)))
    for flow in cash_flows:
        if flow.occurred_at is not None:
            events.append(
                LedgerEvent(
                    flow.occurred_at,
                    "cash_flow",
                    float(flow.amount or 0.0),
                    getattr(flow, "id", None),
                )
            )
    # Cash flow first when timestamps are identical, matching the capital which
    # was available before any trade outcome at that timestamp.
    events.sort(key=lambda item: (item.occurred_at, 0 if item.kind == "cash_flow" else 1, item.source_id or 0))
    return events


def calculate_banked_return_audit(*, current_balance: float, deals: Iterable, cash_flows: Iterable) -> dict:
    """Calculate geometrically linked return subperiods split by cash flows."""
    events = build_ledger_events(deals, cash_flows)
    if not events:
        return {"status": "insufficient_history", "reason": "no_ledger_events", "banked_return_percent": None}

    closing_balance = float(current_balance)
    opening_balance = closing_balance - sum(event.amount for event in events)
    if opening_balance < -0.01:
        return {
            "status": "insufficient_history",
            "reason": "negative_reconstructed_opening_balance",
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "banked_return_percent": None,
        }

    balance = max(0.0, opening_balance)
    subperiod_start_balance = balance if balance > 0 else None
    subperiod_started_at = events[0].occurred_at if balance > 0 else None
    subperiod_trade_profit = 0.0
    subperiod_trade_count = 0
    growth_factor = 1.0
    subperiods: list[dict] = []
    cash_flow_audit: list[dict] = []

    def close_subperiod(end_at: datetime) -> str | None:
        nonlocal growth_factor, subperiod_start_balance, subperiod_started_at
        nonlocal subperiod_trade_profit, subperiod_trade_count
        if subperiod_start_balance is None:
            return None
        if subperiod_start_balance <= 0:
            return "nonpositive_subperiod_opening_balance"
        factor = balance / subperiod_start_balance
        if factor <= 0:
            return "account_loss_reached_or_exceeded_100_percent"
        growth_factor *= factor
        subperiods.append(
            {
                "start_at": subperiod_started_at.isoformat() if subperiod_started_at else None,
                "end_at": end_at.isoformat(),
                "opening_balance": subperiod_start_balance,
                "closing_balance_before_cash_flow": balance,
                "net_trading_profit": subperiod_trade_profit,
                "trade_count": subperiod_trade_count,
                "return_percent": (factor - 1.0) * 100.0,
                "growth_factor": factor,
            }
        )
        subperiod_trade_profit = 0.0
        subperiod_trade_count = 0
        return None

    for event in events:
        if event.kind == "deal":
            if balance <= 0:
                return {
                    "status": "insufficient_history",
                    "reason": "no_invested_capital_before_deal",
                    "banked_return_percent": None,
                }
            balance += event.amount
            subperiod_trade_profit += event.amount
            subperiod_trade_count += 1
            if balance < -0.01:
                return {
                    "status": "insufficient_history",
                    "reason": "negative_balance_after_deal",
                    "banked_return_percent": None,
                }
            balance = max(0.0, balance)
            continue

        # A cash flow ends the current return subperiod before changing capital.
        if subperiod_start_balance is not None:
            reason = close_subperiod(event.occurred_at)
            if reason:
                return {"status": "insufficient_history", "reason": reason, "banked_return_percent": None}

        before = balance
        balance += event.amount
        cash_flow_audit.append(
            {
                "occurred_at": event.occurred_at.isoformat(),
                "amount": event.amount,
                "balance_before": before,
                "balance_after": balance,
                "source_id": event.source_id,
            }
        )
        if balance < -0.01:
            return {
                "status": "insufficient_history",
                "reason": "negative_balance_after_cash_flow",
                "banked_return_percent": None,
            }
        balance = max(0.0, balance)
        subperiod_start_balance = balance if balance > 0 else None
        subperiod_started_at = event.occurred_at if balance > 0 else None

    if subperiod_start_balance is not None:
        reason = close_subperiod(events[-1].occurred_at)
        if reason:
            return {"status": "insufficient_history", "reason": reason, "banked_return_percent": None}

    reconciliation_gap = closing_balance - balance
    status = "available" if abs(reconciliation_gap) <= 0.02 else "review_required"
    return {
        "status": status,
        "reason": None if status == "available" else "ledger_does_not_reconcile_to_current_balance",
        "method": "cash_flow_split_geometrically_linked_balance_return",
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "reconstructed_closing_balance": balance,
        "reconciliation_gap": reconciliation_gap,
        "banked_return_percent": (growth_factor - 1.0) * 100.0 if subperiods else None,
        "growth_factor": growth_factor,
        "deal_count": sum(1 for event in events if event.kind == "deal"),
        "cash_flow_count": sum(1 for event in events if event.kind == "cash_flow"),
        "cash_flows": cash_flow_audit,
        "subperiods": subperiods,
    }


def get_fxblue_banked_return_preview() -> dict:
    stable = get_performance_analytics()
    if stable.get("status") != "success":
        return stable
    account = str(stable.get("master_account") or "").strip()
    if not account:
        return {"status": "error", "message": "No active master account available"}

    db = SessionLocal()
    try:
        latest = (
            db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == account)
            .order_by(EquitySnapshot.timestamp.desc(), EquitySnapshot.id.desc())
            .first()
        )
        if latest is None:
            return {"status": "insufficient_history", "master_account": account, "reason": "no_current_snapshot"}
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
        audit = calculate_banked_return_audit(
            current_balance=float(latest.balance or stable.get("current_balance") or 0.0),
            deals=deals,
            cash_flows=flows,
        )
        return {
            "master_account": account,
            "preview_only": True,
            "production_analytics_unchanged": True,
            "stable_banked_return_percent": stable.get("banked_return_percent"),
            **audit,
        }
    finally:
        db.close()
