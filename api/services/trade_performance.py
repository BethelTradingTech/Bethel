"""Bethel Trading Technologies - production trade and risk analytics.

Statistics are calculated from signed MT5 deals stored in the production
PostgreSQL database. Exit deals are aggregated by MT5 position so partial closes
remain one completed trade.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal


class TradePerformanceEngine:
    def __init__(self):
        self.db = SessionLocal()
        self.account_number = self._active_account_number()
        self.starting_capital = self._funding_base()

    def _active_account_number(self):
        configured = (os.getenv("BETHEL_MASTER_ACCOUNT") or "").strip()
        if configured:
            return configured

        configured_accounts = [
            value.strip()
            for value in (os.getenv("MASTER_MT5_ACCOUNTS") or "").split(",")
            if value.strip()
        ]
        if len(configured_accounts) == 1:
            return configured_accounts[0]

        latest = (
            self.db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number.isnot(None))
            .order_by(EquitySnapshot.timestamp.desc())
            .first()
        )
        return str(latest.account_number).strip() if latest and latest.account_number else None

    def _funding_base(self) -> float:
        if not self.account_number:
            return 0.0

        cash_flows = (
            self.db.query(ConnectorCashFlow)
            .filter(ConnectorCashFlow.account_number == self.account_number)
            .all()
        )
        net_funding = sum(float(item.amount or 0) for item in cash_flows)
        if net_funding > 0:
            return net_funding

        first_snapshot = (
            self.db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == self.account_number)
            .order_by(EquitySnapshot.timestamp.asc())
            .first()
        )
        if not first_snapshot:
            return 0.0
        return float(first_snapshot.balance or first_snapshot.equity or 0)

    def first_trade_at(self):
        """Return the earliest signed MT5 deal timestamp for the active master.

        This is intentionally account-specific and dynamic. It is used by admin
        performance charts to begin at actual trading activity rather than at
        account creation or the first telemetry snapshot.
        """
        if not self.account_number:
            return None
        first_deal = (
            self.db.query(ConnectorDeal)
            .filter(ConnectorDeal.account_number == self.account_number)
            .order_by(ConnectorDeal.closed_at.asc(), ConnectorDeal.id.asc())
            .first()
        )
        return first_deal.closed_at if first_deal else None

    def load_position_results(self) -> List[Tuple[str, float]]:
        """Return completed MT5 positions in chronological closing order."""
        if not self.account_number:
            return []

        deals = (
            self.db.query(ConnectorDeal)
            .filter(ConnectorDeal.account_number == self.account_number)
            .order_by(ConnectorDeal.closed_at.asc(), ConnectorDeal.id.asc())
            .all()
        )
        grouped: Dict[str, Dict] = defaultdict(lambda: {"profit": 0.0, "closed_at": None})
        for deal in deals:
            position_key = str(deal.position_id or deal.deal_ticket)
            grouped[position_key]["profit"] += (
                float(deal.profit or 0)
                + float(deal.commission or 0)
                + float(deal.swap or 0)
                + float(deal.fee or 0)
            )
            if grouped[position_key]["closed_at"] is None or deal.closed_at > grouped[position_key]["closed_at"]:
                grouped[position_key]["closed_at"] = deal.closed_at

        ordered = sorted(grouped.items(), key=lambda item: item[1]["closed_at"])
        return [(position_id, float(values["profit"])) for position_id, values in ordered]

    def profits(self) -> np.ndarray:
        return np.array([profit for _, profit in self.load_position_results()], dtype=float)

    def statistics(self) -> Dict:
        profits = self.profits()
        if len(profits) == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "breakeven_trades": 0,
                "win_rate": 0,
                "gross_profit": 0,
                "gross_loss": 0,
                "profit_factor": 0,
                "average_win": 0,
                "average_loss": 0,
                "payoff_ratio": 0,
                "expectancy": 0,
            }

        wins = profits[profits > 0]
        losses = profits[profits < 0]
        breakeven = profits[profits == 0]
        total = len(profits)
        winners = len(wins)
        losers = len(losses)
        average_win = float(wins.mean()) if winners else 0.0
        average_loss = float(losses.mean()) if losers else 0.0
        gross_profit = float(wins.sum())
        gross_loss = abs(float(losses.sum()))

        return {
            "total_trades": total,
            "winning_trades": winners,
            "losing_trades": losers,
            "breakeven_trades": len(breakeven),
            "win_rate": round((winners / total) * 100, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0,
            "average_win": round(average_win, 2),
            "average_loss": round(average_loss, 2),
            "payoff_ratio": round(average_win / abs(average_loss), 2) if average_loss < 0 else 0,
            "expectancy": round(float(profits.mean()), 2),
        }

    def risk_metrics(self) -> Dict:
        profits = self.profits()
        empty = {
            "sharpe_ratio": 0,
            "sortino_ratio": 0,
            "max_drawdown": 0,
            "value_at_risk_95_amount": 0,
            "value_at_risk_95_percent": 0,
        }
        if len(profits) < 2 or self.starting_capital <= 0:
            return empty

        returns = profits / self.starting_capital
        mean = float(np.mean(returns))
        std = float(np.std(returns, ddof=1))
        sharpe = mean / std if std != 0 else 0

        downside = returns[returns < 0]
        downside_std = float(np.std(downside, ddof=1)) if len(downside) > 1 else 0
        sortino = mean / downside_std if downside_std != 0 else 0

        equity = self.starting_capital + np.cumsum(profits)
        peak = np.maximum.accumulate(equity)
        max_drawdown = abs(float(np.min(equity - peak))) if len(equity) else 0

        percentile_5 = float(np.percentile(returns, 5))
        var_percent = max(0.0, -percentile_5 * 100)
        var_amount = (var_percent / 100) * self.starting_capital

        return {
            "sharpe_ratio": round(float(sharpe), 2),
            "sortino_ratio": round(float(sortino), 2),
            "max_drawdown": round(max_drawdown, 2),
            "value_at_risk_95_amount": round(var_amount, 2),
            "value_at_risk_95_percent": round(var_percent, 2),
        }

    def report(self) -> Dict:
        first_trade = self.first_trade_at()
        return {
            "status": "success",
            "master_account": self.account_number,
            "starting_capital": round(self.starting_capital, 2),
            "first_trade_at": first_trade.isoformat() if first_trade else None,
            "data_source": "signed_connector_deals",
            "performance": self.statistics(),
            "risk": self.risk_metrics(),
        }


def get_trade_performance() -> Dict:
    engine = TradePerformanceEngine()
    try:
        return engine.report()
    finally:
        engine.db.close()
