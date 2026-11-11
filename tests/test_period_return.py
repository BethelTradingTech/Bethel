from datetime import datetime as D
from api.services.period_return import period_return


def test_loss_refunding_and_recovery():
    flows = [(D(2026, 9, 5), 20), (D(2026, 9, 15), 10)]
    for close, profit in [(30, 0), (40, 10), (50, 20)]:
        row = period_return(D(2026, 9, 1), D(2026, 10, 1), 0, close,
                            flows, reconciled=True)
        assert row['trading_gain'] == profit
        assert row['return_percent'] >= 0
        assert (row['return_percent'] > 0) == (profit > 0)


def test_deposit_alone_is_not_profit():
    row = period_return(D(2026, 9, 1), D(2026, 10, 1), 100, 150,
                        [(D(2026, 9, 15), 50)], reconciled=True)
    assert row['return_percent'] == 0


def test_withdrawal_does_not_become_loss():
    row = period_return(D(2026, 9, 1), D(2026, 10, 1), 100, 90,
                        [(D(2026, 9, 15), -20)], reconciled=True)
    assert row['trading_gain'] == 10
    assert row['return_percent'] > 0


def test_missing_or_unreconciled_is_not_fabricated():
    for opening, verified in [(None, True), (100, False)]:
        row = period_return(D(2026, 9, 1), D(2026, 10, 1), opening, 150,
                            [], reconciled=verified)
        assert row['return_percent'] is None


def test_same_formula_for_yearly_period():
    row = period_return(D(2026, 1, 1), D(2027, 1, 1), 100, 130,
                        [(D(2026, 7, 1), 20)], reconciled=True)
    assert row['trading_gain'] == 10
    assert row['return_percent'] > 0
