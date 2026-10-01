from datetime import datetime
from types import SimpleNamespace as Row

from api.services.monthly_equity_performance import completed_month_equity
import pytest


def snap(day, balance, equity, id=1):
    return Row(timestamp=datetime.fromisoformat(day), balance=balance, equity=equity, id=id)


def deal(day, profit):
    return Row(closed_at=datetime.fromisoformat(day), profit=profit, commission=0, swap=0, fee=0)


def test_recovery_improves_grade_without_rewriting_monthly_gain():
    start = snap("2026-08-31T23:00:00", 1000, 1000)
    low = snap("2026-09-12T12:00:00", 700, 700)
    partial = snap("2026-09-30T23:00:00", 800, 800)
    full = snap("2026-09-30T23:00:00", 1100, 1100)
    early = completed_month_equity([start, low, partial], [], [deal("2026-09-12T11:00:00", -300), deal("2026-09-30T12:00:00", 100)], datetime(2026, 10, 1), monthly_returns=[{"month":"2026-09","return_percent":-20}])[-1]
    recovered = completed_month_equity([start, low, full], [], [deal("2026-09-12T11:00:00", -300), deal("2026-09-30T12:00:00", 400)], datetime(2026, 10, 1), monthly_returns=[{"month":"2026-09","return_percent":-20}])[-1]
    assert early["equity_gain"] == -200
    assert recovered["equity_gain"] == 100
    assert recovered["recovery_percent"] == 100
    assert recovered["monthly_score"] > early["monthly_score"]


def test_missing_boundary_or_broker_ledger_gap_withholds_recovery_grade():
    start = snap("2026-08-31T23:00:00", 1000, 1000)
    close = snap("2026-09-30T23:00:00", 1100, 1100)
    missing = completed_month_equity([close], [], [], datetime(2026, 10, 1))[-1]
    gap = completed_month_equity([start, close], [], [], datetime(2026, 10, 1))[-1]
    assert missing["status"] == "boundary_snapshot_missing" and missing["equity_gain"] is None
    assert gap["status"] == "ledger_gap" and gap["monthly_grade"] is None


def test_deposit_does_not_create_recovery():
    rows = [snap("2026-08-31T23:00:00", 1000, 1000),
            snap("2026-09-12T12:00:00", 700, 700),
            snap("2026-09-30T23:00:00", 1200, 1200)]
    flows = [Row(occurred_at=datetime(2026, 9, 20), amount=500)]
    result = completed_month_equity(rows, flows, [deal("2026-09-12T11:00:00", -300)], datetime(2026, 10, 1), monthly_returns=[{"month":"2026-09","return_percent":-30}])[-1]
    assert result["equity_gain"] == -300
    assert result["recovery_percent"] == 0
    assert result["monthly_score"] < 50


def test_positive_dollar_gain_cannot_hide_large_negative_return():
    rows = [snap("2026-08-31T23:00:00", 1000, 1000),
            snap("2026-09-12T12:00:00", 700, 700),
            snap("2026-09-30T23:00:00", 1500, 1500)]
    flow = [Row(occurred_at=datetime(2026, 9, 20), amount=400)]
    result = completed_month_equity(rows, flow, [deal("2026-09-12T11:00:00", -300), deal("2026-09-30T12:00:00", 400)], datetime(2026, 10, 1), monthly_returns=[{"month":"2026-09","return_percent":-88}])[-1]
    assert result["equity_gain"] == 100
    assert result["recovery_percent"] == 100
    assert result["monthly_grade"] == "E"


@pytest.mark.parametrize("ending,profit,recovery,outcome", [
    (30, 0, 100, "break_even"), (40, 10, 150, "profit"), (50, 20, 200, "profit")])
def test_first_month_total_loss_and_refunding(ending, profit, recovery, outcome):
    rows = [snap("2026-09-05T12:00:00", 20, 20),
            snap("2026-09-10T12:00:00", 0, 0),
            snap("2026-09-15T12:00:00", 10, 10),
            snap("2026-09-30T23:00:00", ending, ending)]
    flows = [Row(occurred_at=datetime(2026, 9, 5), amount=20),
             Row(occurred_at=datetime(2026, 9, 15), amount=10)]
    trades = [deal("2026-09-10T11:00:00", -20),
              deal("2026-09-30T12:00:00", ending-10)]
    result = completed_month_equity(rows, flows, trades, datetime(2026, 10, 1))[-1]
    assert result["net_closed_trading_pl"] == profit
    assert result["monthly_profit_result"] == outcome
    assert result["dollar_loss_recovery_percent"] == recovery
    assert result["equity_gain"] is None  # Do not invent historical equity.


def test_deal_only_history_and_funding_do_not_create_recovery():
    trades = [deal("2026-09-10T11:00:00", -20)]
    flows = [Row(occurred_at=datetime(2026, 9, 15), amount=1000)]
    result = completed_month_equity([], flows, trades, datetime(2026, 10, 1))[-1]
    assert result["net_closed_trading_pl"] == -20
    assert result["monthly_profit_result"] == "loss"
    assert result["dollar_loss_recovery_percent"] == 0


def test_closed_recovery_includes_costs_and_resets_each_month():
    loss = deal("2026-08-10T11:00:00", -100)
    gain = deal("2026-09-10T11:00:00", 30)
    gain.commission, gain.swap, gain.fee = -2, -1, -3
    rows = completed_month_equity([], [], [loss, gain], datetime(2026, 10, 1))
    assert rows[1]["net_closed_trading_pl"] == 24
    assert rows[1]["dollar_loss_recovery_percent"] is None
    assert rows[1]["monthly_profit_result"] == "profit"
