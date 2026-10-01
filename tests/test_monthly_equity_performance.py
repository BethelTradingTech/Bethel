from datetime import datetime
from types import SimpleNamespace as Row

from api.services.monthly_equity_performance import completed_month_equity


def snap(day, balance, equity, id=1):
    return Row(timestamp=datetime.fromisoformat(day), balance=balance, equity=equity, id=id)


def deal(day, profit):
    return Row(closed_at=datetime.fromisoformat(day), profit=profit, commission=0, swap=0, fee=0)


def test_recovery_improves_grade_without_rewriting_monthly_gain():
    start = snap("2026-08-31T23:00:00", 1000, 1000)
    low = snap("2026-09-12T12:00:00", 700, 700)
    partial = snap("2026-09-30T23:00:00", 800, 800)
    full = snap("2026-09-30T23:00:00", 1100, 1100)
    early = completed_month_equity([start, low, partial], [], [deal("2026-09-12T11:00:00", -300), deal("2026-09-30T12:00:00", 100)], datetime(2026, 10, 1))[-1]
    recovered = completed_month_equity([start, low, full], [], [deal("2026-09-12T11:00:00", -300), deal("2026-09-30T12:00:00", 400)], datetime(2026, 10, 1))[-1]
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


def test_cash_flow_does_not_create_recovery_or_grade():
    rows = [snap("2026-08-31T23:00:00", 1000, 1000),
            snap("2026-09-12T12:00:00", 700, 700),
            snap("2026-09-30T23:00:00", 1200, 1200)]
    flows = [Row(occurred_at=datetime(2026, 9, 20), amount=500)]
    result = completed_month_equity(rows, flows, [deal("2026-09-12T11:00:00", -300)], datetime(2026, 10, 1))[-1]
    assert result["equity_gain"] == -300
    assert result["recovery_percent"] is None
    assert result["monthly_grade"] is None
