from datetime import datetime
from types import SimpleNamespace

from api.admin_master_performance import _monthly_returns, _yearly_returns


def snapshot(month, day, equity):
    return SimpleNamespace(timestamp=datetime(2026, month, day), equity=equity)


def cashflow(month, day, amount):
    return SimpleNamespace(occurred_at=datetime(2026, month, day), amount=amount)


def test_monthly_return_adjusts_for_deposit():
    rows = _monthly_returns(
        [snapshot(1, 1, 1000), snapshot(1, 31, 1200)],
        [cashflow(1, 15, 100)],
    )
    assert rows == [{
        "month": "2026-01",
        "start_equity": 1000.0,
        "end_equity": 1200.0,
        "net_cash_flow": 100.0,
        "trading_change": 100.0,
        "return_percent": 10.0,
    }]


def test_yearly_return_compounds_months():
    yearly = _yearly_returns([
        {"month": "2026-01", "return_percent": 10.0},
        {"month": "2026-02", "return_percent": -5.0},
    ])
    assert yearly[0]["year"] == 2026
    assert yearly[0]["months"] == {"1": 10.0, "2": -5.0}
    assert yearly[0]["ytd_return_percent"] == 4.5


def test_monthly_rows_do_not_mix_other_month_cashflows():
    rows = _monthly_returns(
        [
            snapshot(1, 1, 1000), snapshot(1, 31, 1100),
            snapshot(2, 1, 1100), snapshot(2, 28, 1210),
        ],
        [cashflow(2, 10, 110)],
    )
    assert rows[0]["return_percent"] == 10.0
    assert rows[1]["return_percent"] == 0.0
