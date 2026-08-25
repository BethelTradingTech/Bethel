from datetime import date

import pytest

from api.services.account_risk_profile import DailyReturn, _track_record_stats


def test_track_record_compounds_monthly_returns_and_drawdown():
    daily = [
        DailyReturn(day=date(2026, 1, 2), value=0.10),
        DailyReturn(day=date(2026, 1, 5), value=0.00),
        DailyReturn(day=date(2026, 2, 2), value=-0.05),
    ]

    stats = _track_record_stats(daily)

    assert stats["monthly_returns"] == [
        {"period": "2026-01", "return_percent": 10.0},
        {"period": "2026-02", "return_percent": -5.0},
    ]
    assert stats["all_time_high_return_percent"] == pytest.approx(10.0)
    assert stats["all_time_high_date"] == "2026-01-02"
    assert stats["current_drawdown_percent"] == pytest.approx(-5.0)
    assert stats["days_since_all_time_high"] == 31


def test_track_record_yearly_return_uses_compounding():
    daily = [
        DailyReturn(day=date(2026, 1, 2), value=0.10),
        DailyReturn(day=date(2026, 2, 2), value=0.10),
    ]

    stats = _track_record_stats(daily)

    assert stats["yearly_returns"] == [
        {"period": "2026", "return_percent": 21.0},
    ]
    assert stats["all_time_high_return_percent"] == pytest.approx(21.0)
    assert stats["current_drawdown_percent"] == pytest.approx(0.0)


def test_track_record_empty_series_fails_closed_to_empty_public_stats():
    stats = _track_record_stats([])

    assert stats["annualized_return_percent"] == 0.0
    assert stats["monthly_returns"] == []
    assert stats["yearly_returns"] == []
    assert stats["all_time_high_date"] is None
