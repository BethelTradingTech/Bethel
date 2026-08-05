"""Bethel Trading Technologies - production trade performance analytics.

Trade statistics are calculated from signed MT5 closed deals stored in Render's
PostgreSQL database. Equity snapshots remain the source for the account baseline.
"""

import os
from collections import defaultdict

import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorDeal


class TradePerformanceEngine:
    def __init__(self):
        self.db = SessionLocal()
        self.account_number = self._active_account_number()
        self.starting_capital = self._starting_capital()

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

    def _starting_capital(self):
        if not self.account_number:
            return 0.0
        first_snapshot = (
            self.db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == self.account_number)
            .order_by(EquitySnapshot.timestamp.asc())
            .first()
        )
        if not first_snapshot:
            return 0.0
        return float(first_snapshot.balance or first_snapshot.equity or 0)

    def load_position_profits(self):
        """Aggregate MT5 exit deals by position, matching the original importer."""
        if not self.account_number:
            return np.array([], dtype=float)

        deals = (
            self.db.query(ConnectorDeal)
            .filter(ConnectorDeal.account_number == self.account_number)
            .order_by(ConnectorDeal.closed_at.asc(), ConnectorDeal.id.asc())
            .all()
        )
        grouped = defaultdict(float)
        for deal in deals:
            position_key = deal.position_id or deal.deal_ticket
            grouped[position_key] += float(deal.profit or 0)
            grouped[position_key] += float(deal.commission or 0)
            grouped[position_key] += float(deal.swap or 0)
            grouped[position_key] += float(deal.fee or 0)
        return np.array(list(grouped.values()), dtype=float)

    def statistics(self):
        profits = self.load_position_profits()
        if len(profits) == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "gross_profit": 0,
                "gross_loss": 0,
                "profit_factor": 0,
                "average_win": 0,
                "average_loss": 0,
                "expectancy": 0,
            }

        wins = profits[profits > 0]
        losses = profits[profits < 0]
        total = len(profits)
        winners = len(wins)
        losers = len(losses)
        gross_profit = float(wins.sum())
        gross_loss = abs(float(losses.sum()))

        return {
            "total_trades": total,
            "winning_trades": winners,
            "losing_trades": losers,
            "win_rate": round((winners / total) * 100, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0,
            "average_win": round(float(wins.mean()), 2) if winners else 0,
            "average_loss": round(float(losses.mean()), 2) if losers else 0,
            "expectancy": round(float(profits.mean()), 2),
        }

    def risk_metrics(self):
        profits = self.load_position_profits()
        if len(profits) < 2 or self.starting_capital <= 0:
            return {"sharpe_ratio": 0, "sortino_ratio": 0, "max_drawdown": 0}

        returns = profits / self.starting_capital
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        sharpe = mean / std if std != 0 else 0

        downside = returns[returns < 0]
        downside_std = np.std(downside, ddof=1) if len(downside) > 1 else 0
        sortino = mean / downside_std if downside_std != 0 else 0

        equity = self.starting_capital + np.cumsum(profits)
        peak = np.maximum.accumulate(equity)
        max_drawdown = abs(float(np.min(equity - peak))) if len(equity) else 0

        return {
            "sharpe_ratio": round(float(sharpe), 2),
            "sortino_ratio": round(float(sortino), 2),
            "max_drawdown": round(max_drawdown, 2),
        }

    def report(self):
        return {
            "status": "success",
            "master_account": self.account_number,
            "starting_capital": round(self.starting_capital, 2),
            "data_source": "signed_connector_deals",
            "performance": self.statistics(),
            "risk": self.risk_metrics(),
        }


def get_trade_performance():
    engine = TradePerformanceEngine()
    try:
        return engine.report()
    finally:
        engine.db.close()
