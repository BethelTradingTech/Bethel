"""Bethel Trading Technologies - Trade Performance Analytics Engine."""

import os
import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot, Trade


class TradePerformanceEngine:
    def __init__(self):
        self.db = SessionLocal()
        self.account_id = self._active_account_id()
        self.starting_capital = self._starting_capital()

    def _active_account_id(self):
        configured = (os.getenv("BETHEL_MASTER_ACCOUNT") or "").strip()
        if configured:
            try:
                return int(configured)
            except ValueError:
                pass

        latest = (
            self.db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number.isnot(None))
            .order_by(EquitySnapshot.timestamp.desc())
            .first()
        )
        if latest and latest.account_number:
            try:
                return int(latest.account_number)
            except (TypeError, ValueError):
                return None
        return None

    def _starting_capital(self):
        if self.account_id is None:
            return 0.0

        first_snapshot = (
            self.db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == str(self.account_id))
            .order_by(EquitySnapshot.timestamp.asc())
            .first()
        )
        if not first_snapshot:
            return 0.0
        return float(first_snapshot.balance or first_snapshot.equity or 0)

    def load_trades(self):
        query = self.db.query(Trade).filter(Trade.status == "CLOSED")
        if self.account_id is not None:
            query = query.filter(Trade.account_id == self.account_id)
        return query.order_by(Trade.closed_at.asc()).all()

    def profits(self):
        return np.array(
            [float(t.profit or 0) for t in self.load_trades()],
            dtype=float,
        )

    def statistics(self):
        profits = self.profits()
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
        win_rate = winners / total * 100
        gross_profit = float(wins.sum())
        gross_loss = abs(float(losses.sum()))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        average_win = float(wins.mean()) if winners else 0
        average_loss = float(losses.mean()) if losers else 0
        expectancy = float(profits.mean())

        return {
            "total_trades": total,
            "winning_trades": winners,
            "losing_trades": losers,
            "win_rate": round(win_rate, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "average_win": round(average_win, 2),
            "average_loss": round(average_loss, 2),
            "expectancy": round(expectancy, 2),
        }

    def risk_metrics(self):
        profits = self.profits()
        if len(profits) < 2 or self.starting_capital <= 0:
            return {"sharpe_ratio": 0, "sortino_ratio": 0, "max_drawdown": 0}

        returns = profits / self.starting_capital
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        sharpe = mean / std if std != 0 else 0

        downside = returns[returns < 0]
        downside_std = np.std(downside, ddof=1) if len(downside) > 1 else 0
        sortino = mean / downside_std if downside_std != 0 else 0

        cumulative_profit = np.cumsum(profits)
        equity = self.starting_capital + cumulative_profit
        peak = np.maximum.accumulate(equity)
        drawdown = equity - peak
        max_drawdown = abs(float(drawdown.min())) if len(drawdown) else 0

        return {
            "sharpe_ratio": round(float(sharpe), 2),
            "sortino_ratio": round(float(sortino), 2),
            "max_drawdown": round(max_drawdown, 2),
        }

    def report(self):
        return {
            "status": "success",
            "master_account": str(self.account_id) if self.account_id is not None else None,
            "starting_capital": round(self.starting_capital, 2),
            "performance": self.statistics(),
            "risk": self.risk_metrics(),
        }


def get_trade_performance():
    engine = TradePerformanceEngine()
    try:
        return engine.report()
    finally:
        engine.db.close()
