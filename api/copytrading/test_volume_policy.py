import pytest

from api.copytrading.volume_policy import (
    calculate_copy_volume,
    cent_capital_multiplier,
)


def test_standard_account_keeps_master_volume():
    assert calculate_copy_volume(0.13, account_type="STANDARD") == 0.13


def test_cent_account_scales_by_starting_capital():
    assert cent_capital_multiplier(500) == 0.5
    assert calculate_copy_volume(
        0.20,
        account_type="CENT",
        starting_capital_usd=500,
    ) == 0.10


def test_cent_account_never_falls_below_minimum_lot():
    assert calculate_copy_volume(
        0.01,
        account_type="CENT",
        starting_capital_usd=100,
    ) == 0.01


@pytest.mark.parametrize("capital", [0, 1000, 2000])
def test_cent_capital_must_be_below_limit(capital):
    with pytest.raises(ValueError):
        cent_capital_multiplier(capital)
