from datetime import datetime
from types import SimpleNamespace

from api.services.ledger_reconciliation import (
    reconciliation_is_acceptable,
    reconciliation_tolerance,
    resolve_opening_balance,
)
from api.services.performance_engine import PerformanceEngine


def test_funded_from_zero_account_is_valid():
    result = resolve_opening_balance(117634.19, 117634.19)
    assert result["status"] == "available"
    assert result["opening_balance"] == 0.0


def test_small_broker_residual_is_normalized_to_zero():
    # Representative of an initial deposit + signed closed-deal ledger whose
    # balance differs by only a few basis points because of broker adjustments.
    result = resolve_opening_balance(117620.63, 117634.19)
    assert result["status"] == "available"
    assert round(result["raw_opening_balance"], 2) == -13.56
    assert result["opening_balance"] == 0.0
    assert result["tolerance"] > 13.56


def test_material_negative_opening_balance_still_fails_closed():
    result = resolve_opening_balance(100000.0, 101000.0)
    assert result["status"] == "not_available"
    assert result["reason"] == "invalid_reconstructed_opening_balance"


def test_reconciliation_accepts_only_small_relative_gap():
    ok, tolerance = reconciliation_is_acceptable(-13.56, 117620.63, 117634.19)
    assert ok is True
    assert tolerance == reconciliation_tolerance(-13.56, 117620.63, 117634.19)

    ok, _ = reconciliation_is_acceptable(-1000.0, 117620.63, 117634.19)
    assert ok is False


def test_starting_capital_uses_verified_initial_funding_before_first_snapshot():
    history = [
        SimpleNamespace(
            timestamp=datetime(2026, 8, 4, 12, 0),
            balance=117929.39,
            equity=117900.0,
        )
    ]
    funding = {
        "first_positive_cash_flow": 100000.0,
        "first_positive_cash_flow_at": datetime(2026, 3, 22, 9, 0),
    }
    assert PerformanceEngine.display_starting_capital(history, funding, 117929.39) == 100000.0


def test_later_topup_does_not_replace_true_snapshot_starting_capital():
    history = [
        SimpleNamespace(
            timestamp=datetime(2026, 3, 1, 12, 0),
            balance=100000.0,
            equity=100000.0,
        )
    ]
    funding = {
        "first_positive_cash_flow": 25000.0,
        "first_positive_cash_flow_at": datetime(2026, 4, 1, 9, 0),
    }
    assert PerformanceEngine.display_starting_capital(history, funding, 100000.0) == 100000.0
