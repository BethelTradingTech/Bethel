"""Bethel Trading Technologies unified performance analytics."""

from __future__ import annotations

import math
import os
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import func

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal
from api.services.trade_performance import get_trade_performance

TRADING_DAYS_PER_YEAR = 252
AVERAGE_DAYS_PER_MONTH = 365.25 / 12


class PerformanceEngine:
    def __init__(self):
        self.db = SessionLocal()

    def active_account_number(self) -> Optional[str]:
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
        if not history:
            return 0.0
        first_balance = float(history[0].balance or 0)
        return first_balance if first_balance > 0 else float(history[0].equity or 0)

    def funding_summary(self, account_number: str, fallback: float) -> Dict:
        cash_flows = (
            self.db.query(ConnectorCashFlow)
            .filter(ConnectorCashFlow.account_number == account_number)
            .order_by(ConnectorCashFlow.occurred_at.asc())
            .all()
        )
        deposits = sum(float(item.amount) for item in cash_flows if float(item.amount) > 0)
        withdrawals = abs(sum(float(item.amount) for item in cash_flows if float(item.amount) < 0))
        net_deposits = deposits - withdrawals
        return {
            "deposits": deposits,
            "withdrawals": withdrawals,
            "net_deposits": net_deposits if net_deposits > 0 else fallback,
            "cash_flow_count": len(cash_flows),
            "first_cash_flow_at": cash_flows[0].occurred_at if cash_flows else None,
            "source": "mt5_cash_flows" if net_deposits > 0 else "first_snapshot_balance",
        }

    def closed_profit_summary(self, account_number: str) -> Dict:
        row = (
            self.db.query(
                func.coalesce(
                    func.sum(
                        ConnectorDeal.profit
                        + ConnectorDeal.commission
                        + ConnectorDeal.swap
                        + ConnectorDeal.fee
                    ),
                    0.0,
                ),
                func.min(ConnectorDeal.closed_at),
                func.max(ConnectorDeal.closed_at),
            )
            .filter(ConnectorDeal.account_number == account_number)
            .one()
        )
        return {
            "net_profit": float(row[0] or 0),
            "first_closed_at": row[1],
            "last_closed_at": row[2],
        }

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
    def period_return(aggregate_return_percent: float, history_days: float, period_days: float) -> float:
        if history_days <= 0 or aggregate_return_percent <= -100:
            return 0.0
        growth = 1 + aggregate_return_percent / 100
        if growth <= 0:
            return 0.0
        return ((growth ** (period_days / history_days)) - 1) * 100

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
        defaults = {
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
            "sharpe_ratio": 0,
            "sortino_ratio": 0,
            "max_drawdown": 0,
            "value_at_risk_95_amount": 0,
            "value_at_risk_95_percent": 0,
        }
        try:
            data = get_trade_performance()
            performance = data.get("performance", {})
            risk = data.get("risk", {})
            return {
                **defaults,
                **{key: performance.get(key, defaults[key]) for key in (
                    "total_trades", "winning_trades", "losing_trades", "breakeven_trades",
                    "win_rate", "gross_profit", "gross_loss", "profit_factor",
                    "average_win", "average_loss", "payoff_ratio", "expectancy",
                )},
                **{key: risk.get(key, defaults[key]) for key in (
                    "sharpe_ratio", "sortino_ratio", "max_drawdown",
                    "value_at_risk_95_amount", "value_at_risk_95_percent",
                )},
            }
        except Exception:
            return defaults

    @staticmethod
    def recovery_factor(total_profit: float, drawdown_amount: float):
        if drawdown_amount <= 0:
            return None
        return round(total_profit / drawdown_amount, 2)

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

    @staticmethod
    def calmar_ratio(banked_return_percent: float, history_days: float, drawdown_percent: float):
        if history_days <= 0 or drawdown_percent <= 0 or banked_return_percent <= -100:
            return None
        annualized_return = (
            ((1 + banked_return_percent / 100) ** (365.25 / history_days)) - 1
        ) * 100
        return round(annualized_return / drawdown_percent, 2)

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

        fallback_capital = self.starting_capital(history)
        funding = self.funding_summary(account_number, fallback_capital)
        closed = self.closed_profit_summary(account_number)
        funding_base = float(funding["net_deposits"] or fallback_capital or 0)

        equity = self.equity_values(history)
        return_series = self.returns(equity)
        current_balance = float(history[-1].balance or 0)
        current_equity = float(history[-1].equity or 0)
        floating_profit = float(history[-1].profit or (current_equity - current_balance))
        closed_profit = float(closed["net_profit"])
        total_profit = closed_profit + floating_profit

        banked_return = (closed_profit / funding_base) * 100 if funding_base > 0 else 0.0
        total_return = (total_profit / funding_base) * 100 if funding_base > 0 else 0.0

        start_candidates = [history[0].timestamp, funding["first_cash_flow_at"], closed["first_closed_at"]]
        start_at = min(value for value in start_candidates if value is not None)
        end_at = history[-1].timestamp
        history_days = max((end_at - start_at).total_seconds() / 86400, 1 / 24)

        daily_return = self.period_return(banked_return, history_days, 1)
        weekly_return = self.period_return(banked_return, history_days, 7)
        monthly_return = self.period_return(banked_return, history_days, AVERAGE_DAYS_PER_MONTH)

        volatility = self.volatility(return_series)
        equity_drawdown_percent = self.equity_drawdown(equity)
        trade_data = self.trade_metrics()
        profit_factor = round(float(trade_data["profit_factor"]), 2)
        drawdown_amount = round(float(trade_data["max_drawdown"]), 2)
        drawdown_percent = (
            (drawdown_amount / funding_base) * 100
            if funding_base > 0 and drawdown_amount > 0
            else equity_drawdown_percent
        )
        recovery = self.recovery_factor(total_profit, drawdown_amount)
        calmar = self.calmar_ratio(banked_return, history_days, drawdown_percent)
        consistency = self.consistency_score(return_series, drawdown_percent, volatility)
        risk = self.risk_level(drawdown_percent, volatility)
        grade = self.performance_grade(total_return, profit_factor, drawdown_percent)

        return {
            "status": "success",
            "master_account": account_number,
            "baseline_source": funding["source"],
            "starting_capital": round(fallback_capital, 2),
            "funding_base": round(funding_base, 2),
            "deposits": round(float(funding["deposits"]), 2),
            "withdrawals": round(float(funding["withdrawals"]), 2),
            "current_balance": round(current_balance, 2),
            "current_equity": round(current_equity, 2),
            "floating_profit_loss": round(floating_profit, 2),
            "closed_profit": round(closed_profit, 2),
            "total_profit": round(total_profit, 2),
            "total_return_percent": round(total_return, 2),
            "banked_return_percent": round(banked_return, 2),
            "daily_return_percent": round(daily_return, 2),
            "weekly_return_percent": round(weekly_return, 2),
            "monthly_return_percent": round(monthly_return, 2),
            "history_days": round(history_days, 2),
            "profit_factor": profit_factor,
            "total_trades": int(trade_data["total_trades"]),
            "winning_trades": int(trade_data["winning_trades"]),
            "losing_trades": int(trade_data["losing_trades"]),
            "breakeven_trades": int(trade_data["breakeven_trades"]),
            "win_rate": round(float(trade_data["win_rate"]), 2),
            "gross_profit": round(float(trade_data["gross_profit"]), 2),
            "gross_loss": round(float(trade_data["gross_loss"]), 2),
            "average_win": round(float(trade_data["average_win"]), 2),
            "average_loss": round(float(trade_data["average_loss"]), 2),
            "payoff_ratio": round(float(trade_data["payoff_ratio"]), 2),
            "expectancy": round(float(trade_data["expectancy"]), 2),
            "sharpe_ratio": round(float(trade_data["sharpe_ratio"]), 2),
            "sortino_ratio": round(float(trade_data["sortino_ratio"]), 2),
            "recovery_factor": recovery,
            "maximum_drawdown_amount": drawdown_amount,
            "maximum_drawdown_percent": round(drawdown_percent, 2),
            "volatility": round(volatility * 100, 2),
            "calmar_ratio": calmar,
            "value_at_risk_95_amount": round(float(trade_data["value_at_risk_95_amount"]), 2),
            "value_at_risk_95_percent": round(float(trade_data["value_at_risk_95_percent"]), 2),
            "consistency_score": consistency,
            "risk_level": risk,
            "performance_grade": grade,
            "cash_flow_events": funding["cash_flow_count"],
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
