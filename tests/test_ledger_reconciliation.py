from api.services.ledger_reconciliation import (
    reconciliation_is_acceptable,
    reconciliation_tolerance,
    resolve_opening_balance,
)


def test_funded_from_zero_account_is_valid():
    result = resolve_opening_balance(117634.19, 117634.19)
    assert result["status"] == "available"
    assert result["opening_balance"] == 0.0


def test_small_broker_residual_is_normalized_to_zero():
    # Representative of an initial deposit + signed closed-deal ledger whose
    # balance differs by only a few basis points because of broker adjustments.
    result = resolve_opening_balance(117620.63, 117634.19)
    assert result["status"] == "available"
    assert result["raw_opening_balance"] == -13.56
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
