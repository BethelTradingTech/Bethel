"""Audited return and risk analytics built from signed MT5 production data.

This module intentionally does not claim to reproduce Darwinex's proprietary
implementation. It follows the methodology Darwinex publicly documents:

* returns are equity based and external cash flows are neutralised;
* monthly VaR uses a 95% confidence level;
* the strategy-risk lookback is the latest 45 exposed-market days;
* forward risk is estimated with Monte Carlo scenarios.

When the required history is unavailable, the API returns an explicit
``insufficient_history`` status instead of a guessed number.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import math
from typing import Iterable, Optional

import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorCashFlow, ConnectorDeal

EXPOSURE_LOOKBACK_DAYS = 45
MONTHLY_HORIZON_TRADING_DAYS = 21
MONTE_CARLO_SCENARIOS = 10_000
BOOTSTRAP_BLOCK_DAYS = 5


@dataclass(frozen=True)
class DailyPoint:
    observed_at: datetime
    equity: float
    balance: float
    floating_profit: float


class AuditedAnalyticsEngine:
    def __init__(self, account_number: str):
        self.account_number = str(account_number).strip()
        self.db = SessionLocal()

    def close(self) -> None:
        self.db.close()

    def _snapshots(self) -> list[EquitySnapshot]:
        return (
            self.db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == self.account_number)
            .order_by(EquitySnapshot.timestamp.asc(), EquitySnapshot.id.asc())
            .all()
        )

    def _cash_flows(self) -> list[ConnectorCashFlow]:
        return (
            self.db.query(ConnectorCashFlow)
            .filter(ConnectorCashFlow.account_number == self.account_number)
            .order_by(ConnectorCashFlow.occurred_at.asc(), ConnectorCashFlow.id.asc())
            .all()
        )

    def _deal_dates(self) -> set:
        rows = (
            self.db.query(ConnectorDeal.closed_at)
            .filter(ConnectorDeal.account_number == self.account_number)
            .all()
        )
        return {row[0].date() for row in rows if row[0] is not None}

    def _history_completeness(self, snapshots: list[EquitySnapshot]) -> dict:
        """Confirm account-labelled snapshots cover the account's trading history.

        Older snapshots can exist without an account number after a master-account
        migration. In that case, filtering by the active account produces a partial
        history. Calculating returns from that partial series can create extreme,
        false results. The engine therefore refuses to calculate until the snapshot
        series begins no later than the first signed cash flow or closed deal.
        """
        if not snapshots or snapshots[0].timestamp is None:
            return {
                "complete": False,
                "reason": "no_signed_equity_snapshots",
                "first_snapshot_at": None,
                "earliest_account_event_at": None,
            }

        first_snapshot_at = snapshots[0].timestamp
        cash_flows = self._cash_flows()
        earliest_cash_flow = next(
            (item.occurred_at for item in cash_flows if item.occurred_at is not None),
            None,
        )
        earliest_deal_row = (
            self.db.query(ConnectorDeal.closed_at)
            .filter(
                ConnectorDeal.account_number == self.account_number,
                ConnectorDeal.closed_at.isnot(None),
            )
            .order_by(ConnectorDeal.closed_at.asc())
            .first()
        )
        earliest_deal = earliest_deal_row[0] if earliest_deal_row else None
        event_candidates = [
            value for value in (earliest_cash_flow, earliest_deal) if value is not None
        ]
        earliest_event = min(event_candidates) if event_candidates else None
        complete = earliest_event is None or first_snapshot_at <= earliest_event
        return {
            "complete": complete,
            "reason": None if complete else "account_snapshot_history_starts_after_trading_history",
            "first_snapshot_at": first_snapshot_at.isoformat(),
            "earliest_account_event_at": earliest_event.isoformat() if earliest_event else None,
        }

    @staticmethod
    def _daily_closes(snapshots: Iterable[EquitySnapshot]) -> list[DailyPoint]:
        closes: OrderedDict = OrderedDict()
        for item in snapshots:
            if item.timestamp is None:
                continue
            equity = float(item.equity or 0)
            balance = float(item.balance or 0)
            if equity <= 0 or balance < 0:
                continue
            closes[item.timestamp.date()] = DailyPoint(
                observed_at=item.timestamp,
                equity=equity,
                balance=balance,
                floating_profit=float(item.profit or (equity - balance)),
            )
        return list(closes.values())

    @staticmethod
    def _modified_dietz_return(
        start: DailyPoint,
        end: DailyPoint,
        cash_flows: Iterable[ConnectorCashFlow],
    ) -> Optional[float]:
        seconds = (end.observed_at - start.observed_at).total_seconds()
        if seconds <= 0 or start.equity <= 0:
            return None

        net_flow = 0.0
        weighted_flow = 0.0
        for flow in cash_flows:
            when = flow.occurred_at
            if when is None or not (start.observed_at < when <= end.observed_at):
                continue
            amount = float(flow.amount or 0)
            remaining_weight = max(
                0.0,
                min(1.0, (end.observed_at - when).total_seconds() / seconds),
            )
            net_flow += amount
            weighted_flow += remaining_weight * amount

        denominator = start.equity + weighted_flow
        if denominator <= 0:
            return None
        value = (end.equity - start.equity - net_flow) / denominator
        return float(value) if math.isfinite(value) and value > -1 else None

    @staticmethod
    def _compound(values: Iterable[float]) -> Optional[float]:
        data = np.asarray(list(values), dtype=float)
        data = data[np.isfinite(data)]
        if len(data) == 0 or np.any(data <= -1):
            return None
        growth = float(np.prod(1.0 + data))
        return (growth - 1.0) * 100.0 if math.isfinite(growth) and growth > 0 else None

    def _daily_returns(self) -> list[tuple[datetime, float, bool]]:
        points = self._daily_closes(self._snapshots())
        flows = self._cash_flows()
        deal_dates = self._deal_dates()
        result: list[tuple[datetime, float, bool]] = []
        for index in range(1, len(points)):
            start, end = points[index - 1], points[index]
            value = self._modified_dietz_return(start, end, flows)
            if value is None:
                continue
            exposed = (
                end.observed_at.date() in deal_dates
                or abs(start.floating_profit) > 1e-9
                or abs(end.floating_profit) > 1e-9
                or abs(end.balance - start.balance) > 1e-9
            )
            result.append((end.observed_at, value, exposed))
        return result

    @staticmethod
    def _period_return(
        daily_returns: list[tuple[datetime, float, bool]],
        start_at: datetime,
    ) -> Optional[float]:
        return AuditedAnalyticsEngine._compound(
            value for observed_at, value, _ in daily_returns if observed_at >= start_at
        )

    def returns_report(self) -> dict:
        snapshots = self._snapshots()
        if not snapshots:
            return {
                "status": "not_available",
                "reason": "no_signed_equity_snapshots",
                "method": "cash_flow_adjusted_equity_modified_dietz",
            }

        completeness = self._history_completeness(snapshots)
        if not completeness["complete"]:
            return {
                "status": "insufficient_history",
                "reason": completeness["reason"],
                "method": "cash_flow_adjusted_equity_modified_dietz_compounded",
                "source": "signed_mt5_equity_snapshots_and_cash_flows",
                "first_snapshot_at": completeness["first_snapshot_at"],
                "earliest_account_event_at": completeness["earliest_account_event_at"],
                "daily_observations": 0,
                "since_inception_return_percent": None,
                "rolling_1d_return_percent": None,
                "rolling_1w_return_percent": None,
                "rolling_1m_return_percent": None,
            }

        daily_returns = self._daily_returns()
        end_at = snapshots[-1].timestamp
        first_at = snapshots[0].timestamp
        since_inception = self._compound(value for _, value, _ in daily_returns)
        one_day = self._compound([daily_returns[-1][1]]) if daily_returns else None
        one_week = self._period_return(daily_returns, end_at - timedelta(days=7))
        one_month = self._period_return(daily_returns, end_at - timedelta(days=30))

        return {
            "status": "available" if daily_returns else "insufficient_history",
            "method": "cash_flow_adjusted_equity_modified_dietz_compounded",
            "source": "signed_mt5_equity_snapshots_and_cash_flows",
            "period_start": first_at.isoformat() if first_at else None,
            "period_end": end_at.isoformat() if end_at else None,
            "daily_observations": len(daily_returns),
            "since_inception_return_percent": round(since_inception, 4) if since_inception is not None else None,
            "rolling_1d_return_percent": round(one_day, 4) if one_day is not None else None,
            "rolling_1w_return_percent": round(one_week, 4) if one_week is not None else None,
            "rolling_1m_return_percent": round(one_month, 4) if one_month is not None else None,
        }

    def _rng(self) -> np.random.Generator:
        digest = hashlib.sha256(self.account_number.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big", signed=False)
        return np.random.default_rng(seed)

    @staticmethod
    def _block_bootstrap_months(
        exposed_returns: np.ndarray,
        rng: np.random.Generator,
    ) -> np.ndarray:
        count = len(exposed_returns)
        blocks_needed = math.ceil(MONTHLY_HORIZON_TRADING_DAYS / BOOTSTRAP_BLOCK_DAYS)
        scenarios = np.empty(MONTE_CARLO_SCENARIOS, dtype=float)
        for scenario in range(MONTE_CARLO_SCENARIOS):
            path: list[float] = []
            for _ in range(blocks_needed):
                start = int(rng.integers(0, count))
                for offset in range(BOOTSTRAP_BLOCK_DAYS):
                    path.append(float(exposed_returns[(start + offset) % count]))
            month = np.asarray(path[:MONTHLY_HORIZON_TRADING_DAYS], dtype=float)
            scenarios[scenario] = float(np.prod(1.0 + month) - 1.0)
        return scenarios

    def risk_report(self) -> dict:
        snapshots = self._snapshots()
        completeness = self._history_completeness(snapshots)
        if not completeness["complete"]:
            return {
                "status": "insufficient_history",
                "reason": completeness["reason"],
                "method": "monthly_95_var_block_bootstrap_monte_carlo",
                "source": "signed_mt5_cash_flow_adjusted_exposed_day_equity_returns",
                "required_exposed_days": EXPOSURE_LOOKBACK_DAYS,
                "available_exposed_days": 0,
                "monthly_horizon_trading_days": MONTHLY_HORIZON_TRADING_DAYS,
                "confidence_percent": 95,
                "scenario_count": MONTE_CARLO_SCENARIOS,
                "monthly_var_95_percent": None,
                "monthly_expected_shortfall_95_percent": None,
            }

        daily = self._daily_returns()
        exposed = np.asarray([value for _, value, is_exposed in daily if is_exposed], dtype=float)
        exposed = exposed[np.isfinite(exposed)]
        if len(exposed) < EXPOSURE_LOOKBACK_DAYS:
            return {
                "status": "insufficient_history",
                "method": "monthly_95_var_block_bootstrap_monte_carlo",
                "source": "signed_mt5_cash_flow_adjusted_exposed_day_equity_returns",
                "required_exposed_days": EXPOSURE_LOOKBACK_DAYS,
                "available_exposed_days": int(len(exposed)),
                "monthly_horizon_trading_days": MONTHLY_HORIZON_TRADING_DAYS,
                "confidence_percent": 95,
                "scenario_count": MONTE_CARLO_SCENARIOS,
                "monthly_var_95_percent": None,
                "monthly_expected_shortfall_95_percent": None,
            }

        sample = exposed[-EXPOSURE_LOOKBACK_DAYS:]
        scenarios = self._block_bootstrap_months(sample, self._rng())
        losses = -scenarios
        var = max(0.0, float(np.percentile(losses, 95)))
        tail = losses[losses >= var]
        expected_shortfall = max(0.0, float(np.mean(tail))) if len(tail) else var
        return {
            "status": "available",
            "method": "monthly_95_var_block_bootstrap_monte_carlo",
            "source": "signed_mt5_cash_flow_adjusted_exposed_day_equity_returns",
            "lookback_exposed_days": EXPOSURE_LOOKBACK_DAYS,
            "monthly_horizon_trading_days": MONTHLY_HORIZON_TRADING_DAYS,
            "confidence_percent": 95,
            "scenario_count": MONTE_CARLO_SCENARIOS,
            "monthly_var_95_percent": round(var * 100.0, 4),
            "monthly_expected_shortfall_95_percent": round(expected_shortfall * 100.0, 4),
        }

    def report(self) -> dict:
        return {
            "status": "success",
            "master_account": self.account_number,
            "return_analytics": self.returns_report(),
            "risk_analytics": self.risk_report(),
        }


def get_audited_analytics(account_number: str) -> dict:
    engine = AuditedAnalyticsEngine(account_number)
    try:
        return engine.report()
    finally:
        engine.close()
