from datetime import datetime, timedelta
from types import SimpleNamespace

import numpy as np

from api.services.analytics_v2 import (
    AuditedAnalyticsEngine,
    DailyPoint,
    EXPOSURE_LOOKBACK_DAYS,
)


def point(day: int, equity: float) -> DailyPoint:
    return DailyPoint(
        observed_at=datetime(2026, 1, day, 23, 59),
        equity=equity,
        balance=equity,
        floating_profit=0.0,
    )


def test_modified_dietz_neutralises_deposit():
    start = point(1, 1000.0)
    end = point(2, 1600.0)
    deposit = SimpleNamespace(
        occurred_at=start.observed_at + timedelta(hours=12),
        amount=500.0,
    )

    result = AuditedAnalyticsEngine._modified_dietz_return(start, end, [deposit])

    assert result is not None
    assert round(result * 100, 4) == 8.0


def test_modified_dietz_does_not_count_pure_deposit_as_profit():
    start = point(1, 1000.0)
    end = point(2, 1500.0)
    deposit = SimpleNamespace(
        occurred_at=start.observed_at + timedelta(hours=12),
        amount=500.0,
    )

    result = AuditedAnalyticsEngine._modified_dietz_return(start, end, [deposit])

    assert result == 0.0


def test_compound_return_links_subperiods():
    result = AuditedAnalyticsEngine._compound([0.10, -0.05, 0.02])
    assert result is not None
    assert round(result, 4) == 6.59


def test_monthly_bootstrap_is_deterministic_for_seeded_rng():
    returns = np.linspace(-0.01, 0.015, EXPOSURE_LOOKBACK_DAYS)
    first = AuditedAnalyticsEngine._block_bootstrap_months(
        returns, np.random.default_rng(12345)
    )
    second = AuditedAnalyticsEngine._block_bootstrap_months(
        returns, np.random.default_rng(12345)
    )

    assert len(first) == 10_000
    assert np.array_equal(first, second)
    assert np.all(np.isfinite(first))


def test_risk_report_refuses_to_guess_before_45_exposed_days():
    engine = object.__new__(AuditedAnalyticsEngine)
    engine.account_number = "TEST-ACCOUNT"
    engine._daily_returns = lambda: [
        (datetime(2026, 1, 1) + timedelta(days=index), 0.001, True)
        for index in range(EXPOSURE_LOOKBACK_DAYS - 1)
    ]

    report = engine.risk_report()

    assert report["status"] == "insufficient_history"
    assert report["required_exposed_days"] == EXPOSURE_LOOKBACK_DAYS
    assert report["available_exposed_days"] == EXPOSURE_LOOKBACK_DAYS - 1
    assert report["monthly_var_95_percent"] is None
    assert report["monthly_expected_shortfall_95_percent"] is None


def test_risk_report_becomes_available_at_45_exposed_days():
    engine = object.__new__(AuditedAnalyticsEngine)
    engine.account_number = "TEST-ACCOUNT"
    returns = np.linspace(-0.015, 0.012, EXPOSURE_LOOKBACK_DAYS)
    engine._daily_returns = lambda: [
        (datetime(2026, 1, 1) + timedelta(days=index), float(value), True)
        for index, value in enumerate(returns)
    ]

    first = engine.risk_report()
    second = engine.risk_report()

    assert first["status"] == "available"
    assert first["lookback_exposed_days"] == EXPOSURE_LOOKBACK_DAYS
    assert first["scenario_count"] == 10_000
    assert first["monthly_var_95_percent"] is not None
    assert first["monthly_expected_shortfall_95_percent"] is not None
    assert first["monthly_var_95_percent"] >= 0
    assert first["monthly_expected_shortfall_95_percent"] >= first["monthly_var_95_percent"]
    assert first == second


def test_non_exposed_days_do_not_satisfy_var_gate():
    engine = object.__new__(AuditedAnalyticsEngine)
    engine.account_number = "TEST-ACCOUNT"
    engine._daily_returns = lambda: [
        (datetime(2026, 1, 1) + timedelta(days=index), 0.001, index < 10)
        for index in range(60)
    ]

    report = engine.risk_report()

    assert report["status"] == "insufficient_history"
    assert report["available_exposed_days"] == 10
