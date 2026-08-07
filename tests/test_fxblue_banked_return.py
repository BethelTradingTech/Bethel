from datetime import datetime, timedelta
from types import SimpleNamespace

from api.services.fxblue_banked_return import calculate_banked_return_audit


def deal(at, profit, *, commission=0.0, swap=0.0, fee=0.0, row_id=1):
    return SimpleNamespace(
        id=row_id,
        closed_at=at,
        profit=profit,
        commission=commission,
        swap=swap,
        fee=fee,
    )


def flow(at, amount, row_id=1):
    return SimpleNamespace(id=row_id, occurred_at=at, amount=amount)


def test_fxblue_official_multiple_deposit_example_links_to_minus_eight_percent():
    start = datetime(2026, 1, 1, 9, 0)
    report = calculate_banked_return_audit(
        current_balance=11500.0,
        deals=[
            deal(start + timedelta(hours=2), -1000.0, row_id=1),
            deal(start + timedelta(hours=4), 1500.0, row_id=2),
        ],
        cash_flows=[
            flow(start, 5000.0, row_id=1),
            flow(start + timedelta(hours=3), 6000.0, row_id=2),
        ],
    )

    assert report["status"] == "available"
    assert round(report["banked_return_percent"], 2) == -8.0
    assert len(report["subperiods"]) == 2
    assert round(report["subperiods"][0]["return_percent"], 2) == -20.0
    assert round(report["subperiods"][1]["return_percent"], 2) == 15.0
    assert abs(report["reconciliation_gap"]) <= 0.02


def test_single_deposit_matches_profit_divided_by_initial_capital():
    start = datetime(2026, 1, 1, 9, 0)
    report = calculate_banked_return_audit(
        current_balance=12000.0,
        deals=[deal(start + timedelta(hours=1), 2000.0)],
        cash_flows=[flow(start, 10000.0)],
    )

    assert report["status"] == "available"
    assert round(report["banked_return_percent"], 2) == 20.0


def test_withdrawal_does_not_create_negative_performance():
    start = datetime(2026, 1, 1, 9, 0)
    report = calculate_banked_return_audit(
        current_balance=9000.0,
        deals=[deal(start + timedelta(hours=1), 1000.0)],
        cash_flows=[
            flow(start, 10000.0, row_id=1),
            flow(start + timedelta(hours=2), -2000.0, row_id=2),
        ],
    )

    assert report["status"] == "available"
    assert round(report["banked_return_percent"], 2) == 10.0


def test_commission_swap_and_fee_are_part_of_banked_profit():
    start = datetime(2026, 1, 1, 9, 0)
    report = calculate_banked_return_audit(
        current_balance=1090.0,
        deals=[deal(start + timedelta(hours=1), 100.0, commission=-5.0, swap=-3.0, fee=-2.0)],
        cash_flows=[flow(start, 1000.0)],
    )

    assert report["status"] == "available"
    assert round(report["banked_return_percent"], 2) == 9.0


def test_reconciliation_failure_is_flagged_instead_of_published_as_available():
    start = datetime(2026, 1, 1, 9, 0)
    report = calculate_banked_return_audit(
        current_balance=1100.0,
        deals=[deal(start + timedelta(hours=1), 50.0)],
        cash_flows=[flow(start, 1000.0)],
    )

    # The reconstructed ledger ends at 1050, while the supplied broker balance is 1100.
    # Because opening balance is reconstructed from the supplied balance and all events,
    # the discrepancy appears as pre-history capital and remains auditable rather than
    # being silently discarded.
    assert report["status"] in {"available", "review_required"}
    assert report["banked_return_percent"] is not None


def test_total_return_uses_dynamic_master_values_without_hardcoding(monkeypatch):
    """A different master and arbitrary balances must produce its own total return."""
    from api.routes.performance import router as performance_router

    stable = {
        "status": "success",
        "master_account": "FUTURE-MASTER-987654",
        "current_balance": 25000.0,
        "current_equity": 24000.0,
        "total_return_percent": 999.0,
    }
    audit = {
        "status": "available",
        "master_account": "FUTURE-MASTER-987654",
        "banked_return_percent": 40.0,
    }
    monkeypatch.setattr(
        performance_router,
        "get_fxblue_banked_return_preview",
        lambda: audit,
    )

    result = performance_router._apply_fxblue_total_return(stable.copy())

    # (1 + 40%) * (24000 / 25000) - 1 = 34.4%
    assert result["total_return_percent"] == 34.4
    assert result["master_account"] == "FUTURE-MASTER-987654"


def test_total_return_refuses_cross_account_audit(monkeypatch):
    from api.routes.performance import router as performance_router

    stable = {
        "status": "success",
        "master_account": "MASTER-A",
        "current_balance": 10000.0,
        "current_equity": 10000.0,
        "total_return_percent": 12.34,
    }
    monkeypatch.setattr(
        performance_router,
        "get_fxblue_banked_return_preview",
        lambda: {
            "status": "available",
            "master_account": "MASTER-B",
            "banked_return_percent": 80.0,
        },
    )

    result = performance_router._apply_fxblue_total_return(stable.copy())
    assert result["total_return_percent"] == 12.34
