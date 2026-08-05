"""Bethel Trading Technologies unified performance analytics."""

from __future__ import annotations

import math
import os
from typing import Dict, List, Optional

import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.services.trade_performance import get_trade_performance

TRADING_DAYS_PER_YEAR = 252


class PerformanceEngine:
    def __init__(self):
        self.db = SessionLocal()

    def active_account_number(self) -> Optional[str]:
        """Resolve the current master account without a hard-coded account number."""
        configured = os.getenv("BETHEL_MASTER_ACCOUNT", "").strip()
        if configured:
            return configured

        latest = (
            self.db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number.isnot(None))
            .order_by(EquitySnapshot.timestamp.desc())
            .first()
        )
        return str(latest.account_number).strip() if latest and latest.account_number else None

    def load_history(self, account_number: str) -> List[EquitySnapshot]:
        return (
            self.db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == account_number)
            .order_by(EquitySnapshot.timestamp.asc())
            .all()
        )

    @staticmethod
    def starting_capital(history: List[EquitySnapshot]) -> float:
        """Use the first recorded balance for the active master account as baseline."""
        if not history:
            return 0.0
        first_balance = float(history[0].balance or 0)
        if first_balance > 0:
            return first_balance
        return float(history[0].equity or 0)

    @staticmethod
    def equity_values(history: List[EquitySnapshot]) -> np.ndarray:
        return np.array([float(item.equity) for item in history], dtype=float)

    @staticmethod
    def returns(equity: np.ndarray) -> np.ndarray:
        if len(equity) < 2:
            return np.array([])
        denominator = np.where(equity[:-1] == 0, np.nan, equity[:-1])
        values = np.diff(equity) / denominator
        return values[np.isfinite(values)]

    @staticmethod
    def total_return(current_equity: float, starting_capital: float) -> float:
        if starting_capital <= 0:
            return 0.0
        return ((current_equity - starting_capital) / starting_capital) * 100

    @staticmethod
    def daily_return(returns: np.ndarray) -> float:
        if len(returns) == 0:
            return 0.0
        return round(float(np.mean(returns)) * 100, 4)

    @staticmethod
    def monthly_return(returns: np.ndarray) -> float:
        if len(returns) == 0:
            return 0.0
        return round((((1 + np.mean(returns)) ** 21) - 1) * 100, 2)

    @staticmethod
    def volatility(returns: np.ndarray) -> float:
        if len(returns) < 2:
            return 0.0
        return float(np.std(returns, ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))

    @staticmethod
    def equity_drawdown(equity: np.ndarray) -> float:
        if len(equity) == 0:
            return 0.0
        peak = np.maximum.accumulate(equity)
        valid_peak = np.where(peak == 0, np.nan, peak)
        drawdown = (equity - peak) / valid_peak
        finite = drawdown[np.isfinite(drawdown)]
        return abs(float(np.min(finite))) * 100 if len(finite) else 0.0

    @staticmethod
    def trade_metrics() -> Dict:
        try:
            data = get_trade_performance()
            performance = data.get("performance", {})
            risk = data.get("risk", {})
            return {
                "total_trades": performance.get("total_trades", 0),
                "win_rate": performance.get("win_rate", 0),
                "profit_factor": performance.get("profit_factor", 0),
                "sharpe_ratio": risk.get("sharpe_ratio", 0),
                "sortino_ratio": risk.get("sortino_ratio", 0),
                "max_drawdown": risk.get("max_drawdown", 0),
            }
        except Exception:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "sortino_ratio": 0,
                "max_drawdown": 0,
            }

    @staticmethod
    def sharpe_ratio(returns: np.ndarray, trade_data: Dict) -> float:
        value = trade_data.get("sharpe_ratio", 0)
        if value:
            return round(float(value), 2)
        if len(returns) < 2:
            return 0.0
        deviation = np.std(returns, ddof=1)
        if deviation == 0:
            return 0.0
        return round(float((np.mean(returns) / deviation) * math.sqrt(TRADING_DAYS_PER_YEAR)), 2)

    @staticmethod
    def sortino_ratio(returns: np.ndarray, trade_data: Dict) -> float:
        value = trade_data.get("sortino_ratio", 0)
        if value:
            return round(float(value), 2)
        downside = returns[returns < 0]
        if len(downside) < 2:
            return 0.0
        deviation = np.std(downside, ddof=1)
        if deviation == 0:
            return 0.0
        return round(float((np.mean(returns) / deviation) * math.sqrt(TRADING_DAYS_PER_YEAR)), 2)

    @staticmethod
    def recovery_factor(current_equity: float, starting_capital: float, drawdown_amount: float):
        if drawdown_amount <= 0:
            return None
        return round((current_equity - starting_capital) / drawdown_amount, 2)

    @staticmethod
    def consistency_score(returns: np.ndarray, max_drawdown_percent: float, volatility: float) -> float:
        if len(returns) == 0:
            return 0.0
        positive = (np.sum(returns > 0) / len(returns)) * 100
        drawdown_score = max(0, 100 - (max_drawdown_percent * 10))
        volatility_score = max(0, 100 - (volatility * 100))
        score = positive * 0.4 + drawdown_score * 0.3 + volatility_score * 0.3
        return round(min(100, max(0, score)), 2)

    @staticmethod
    def risk_level(drawdown_percent: float, volatility: float) -> str:
        if drawdown_percent < 5 and volatility < 0.10:
            return "LOW"
        if drawdown_percent < 10 and volatility < 0.20:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def performance_grade(total_return: float, profit_factor: float, drawdown_percent: float) -> str:
        if total_return >= 20 and profit_factor >= 3 and drawdown_percent < 5:
            return "A+"
        if total_return >= 10 and profit_factor >= 2 and drawdown_percent < 10:
            return "A"
        if total_return > 0 and profit_factor >= 1.5:
            return "B"
        return "C"

    def generate_report(self) -> Dict:
        account_number = self.active_account_number()
        if not account_number:
            return {"status": "error", "message": "No active master account available"}

        history = self.load_history(account_number)
        if not history:
            return {
                "status": "error",
                "message": f"No equity history available for master account {account_number}",
                "master_account": account_number,
            }

        starting_capital = self.starting_capital(history)
        equity = self.equity_values(history)
        return_series = self.returns(equity)
        current_equity = float(equity[-1])
        total_return = self.total_return(current_equity, starting_capital)
        volatility = self.volatility(return_series)
        equity_drawdown_percent = self.equity_drawdown(equity)

        trade_data = self.trade_metrics()
        profit_factor = round(float(trade_data.get("profit_factor", 0)), 2)
        drawdown_amount = round(float(trade_data.get("max_drawdown", 0)), 2)
        drawdown_percent = (
            (drawdown_amount / starting_capital) * 100
            if starting_capital > 0 and drawdown_amount > 0
            else equity_drawdown_percent
        )

        return {
            "status": "success",
            "master_account": account_number,
            "baseline_source": "first_snapshot_balance",
            "starting_capital": round(starting_capital, 2),
            "current_equity": round(current_equity, 2),
            "total_return_percent": round(total_return, 2),
            "daily_return_percent": self.daily_return(return_series),
            "monthly_return_percent": self.monthly_return(return_series),
            "volatility": round(volatility * 100, 2),
            "maximum_drawdown_amount": drawdown_amount,
            "maximum_drawdown_percent": round(drawdown_percent, 2),
            "profit_factor": profit_factor,
            "sharpe_ratio": self.sharpe_ratio(return_series, trade_data),
            "sortino_ratio": self.sortino_ratio(return_series, trade_data),
            "recovery_factor": self.recovery_factor(current_equity, starting_capital, drawdown_amount),
            "consistency_score": self.consistency_score(return_series, drawdown_percent, volatility),
            "risk_level": self.risk_level(drawdown_percent, volatility),
            "performance_grade": self.performance_grade(total_return, profit_factor, drawdown_percent),
            "total_trades": trade_data.get("total_trades", 0),
            "win_rate": trade_data.get("win_rate", 0),
            "snapshots_analyzed": len(history),
        }

    def close(self):
        if self.db:
            self.db.close()


def get_performance_analytics() -> Dict:
    engine = PerformanceEngine()
    try:
        return engine.generate_report()
    finally:
        engine.close()
