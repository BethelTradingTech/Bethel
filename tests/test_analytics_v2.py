from datetime import datetime, timedelta
from types import SimpleNamespace

import numpy as np

from api.services.analytics_v2 import AuditedAnalyticsEngine, DailyPoint


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

    # Economic profit is 100 on capital weighted by the mid-period deposit.
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
    returns = np.linspace(-0.01, 0.015, 45)
    first = AuditedAnalyticsEngine._block_bootstrap_months(
        returns, np.random.default_rng(12345)
    )
    second = AuditedAnalyticsEngine._block_bootstrap_months(
        returns, np.random.default_rng(12345)
    )

    assert len(first) == 10_000
    assert np.array_equal(first, second)
    assert np.all(np.isfinite(first))
