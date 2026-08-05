from datetime import datetime, timedelta
from types import SimpleNamespace

from api.services.period_returns import build_events, rolling_balance_twr


def deal(at, profit, commission=0.0, swap=0.0, fee=0.0):
    return SimpleNamespace(
        closed_at=at,
        profit=profit,
        commission=commission,
        swap=swap,
        fee=fee,
    )


def flow(at, amount):
    return SimpleNamespace(occurred_at=at, amount=amount)


def test_period_return_uses_only_events_inside_requested_window():
    end_at = datetime(2026, 8, 5, 12, 0)
    deals = [
        deal(end_at - timedelta(days=2), 100.0),
        deal(end_at - timedelta(hours=12), 50.0),
    ]

    report = rolling_balance_twr(
        current_balance=1150.0,
        deals=deals,
        cash_flows=[],
        end_at=end_at,
        period_days=1,
    )

    assert report["status"] == "available"
    assert report["deal_count"] == 1
    assert round(report["opening_balance"], 2) == 1100.0
    assert round(report["return_percent"], 4) == round((50.0 / 1100.0) * 100, 4)


def test_deposit_does_not_create_performance():
    end_at = datetime(2026, 8, 5, 12, 0)
    report = rolling_balance_twr(
        current_balance=1500.0,
        deals=[],
        cash_flows=[flow(end_at - timedelta(hours=6), 500.0)],
        end_at=end_at,
        period_days=1,
    )

    assert report["status"] == "available"
    assert report["cash_flow_count"] == 1
    assert report["return_percent"] == 0.0


def test_withdrawal_does_not_create_loss():
    end_at = datetime(2026, 8, 5, 12, 0)
    report = rolling_balance_twr(
        current_balance=800.0,
        deals=[],
        cash_flows=[flow(end_at - timedelta(hours=6), -200.0)],
        end_at=end_at,
        period_days=1,
    )

    assert report["status"] == "available"
    assert report["cash_flow_count"] == 1
    assert report["return_percent"] == 0.0


def test_deals_are_compounded_using_balance_before_each_deal():
    end_at = datetime(2026, 8, 5, 12, 0)
    deals = [
        deal(end_at - timedelta(hours=8), 100.0),
        deal(end_at - timedelta(hours=4), -55.0),
    ]

    report = rolling_balance_twr(
        current_balance=1045.0,
        deals=deals,
        cash_flows=[],
        end_at=end_at,
        period_days=1,
    )

    expected = ((1 + 100.0 / 1000.0) * (1 - 55.0 / 1100.0) - 1) * 100
    assert report["status"] == "available"
    assert round(report["return_percent"], 8) == round(expected, 8)


def test_commission_swap_and_fee_are_included_in_net_deal_profit():
    end_at = datetime(2026, 8, 5, 12, 0)
    report = rolling_balance_twr(
        current_balance=1090.0,
        deals=[deal(end_at - timedelta(hours=2), 100.0, commission=-5.0, swap=-3.0, fee=-2.0)],
        cash_flows=[],
        end_at=end_at,
        period_days=1,
    )

    assert report["status"] == "available"
    assert round(report["return_percent"], 4) == 9.0


def test_same_timestamp_cash_flow_is_processed_before_deal():
    at = datetime(2026, 8, 5, 10, 0)
    events = build_events(
        [deal(at, 100.0)],
        [flow(at, 500.0)],
        at - timedelta(days=1),
    )

    assert [event.kind for event in events] == ["cash_flow", "deal"]


def test_nonpositive_reconstructed_opening_balance_is_rejected():
    end_at = datetime(2026, 8, 5, 12, 0)
    report = rolling_balance_twr(
        current_balance=100.0,
        deals=[deal(end_at - timedelta(hours=2), 150.0)],
        cash_flows=[],
        end_at=end_at,
        period_days=1,
    )

    assert report["status"] == "insufficient_history"
    assert report["reason"] == "nonpositive_reconstructed_opening_balance"
    assert report["return_percent"] is None
