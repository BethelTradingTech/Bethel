from api.services.normalized_returns import normalized_compound_returns


def test_reproduces_fxblue_account_37371080_screenshot():
    report = normalized_compound_returns(
        banked_return_percent=51.92,
        trading_days=19,
    )

    assert report["status"] == "available"
    assert round(report["daily_return_percent"], 2) == 2.23
    assert round(report["weekly_return_percent"], 2) == 11.63
    assert round(report["monthly_return_percent"], 2) == 58.76


def test_weekly_and_monthly_are_compounded_from_unrounded_daily_factor():
    report = normalized_compound_returns(
        banked_return_percent=51.92,
        trading_days=19,
    )

    daily_factor = 1.0 + report["daily_return_percent"] / 100.0
    assert round((daily_factor**5 - 1.0) * 100.0, 10) == round(
        report["weekly_return_percent"], 10
    )
    assert round((daily_factor**21 - 1.0) * 100.0, 10) == round(
        report["monthly_return_percent"], 10
    )


def test_zero_return_stays_zero_for_all_equivalent_periods():
    report = normalized_compound_returns(
        banked_return_percent=0.0,
        trading_days=19,
    )

    assert report["status"] == "available"
    assert report["daily_return_percent"] == 0.0
    assert report["weekly_return_percent"] == 0.0
    assert report["monthly_return_percent"] == 0.0


def test_negative_return_compounds_without_changing_sign():
    report = normalized_compound_returns(
        banked_return_percent=-25.69,
        trading_days=1820,
    )

    assert report["status"] == "available"
    assert report["daily_return_percent"] < 0
    assert report["weekly_return_percent"] < 0
    assert report["monthly_return_percent"] < 0


def test_rejects_zero_trading_days():
    report = normalized_compound_returns(
        banked_return_percent=51.92,
        trading_days=0,
    )

    assert report["status"] == "insufficient_history"
    assert report["reason"] == "nonpositive_trading_day_count"
    assert report["daily_return_percent"] is None


def test_rejects_total_loss_or_worse():
    for value in (-100.0, -110.0):
        report = normalized_compound_returns(
            banked_return_percent=value,
            trading_days=19,
        )
        assert report["status"] == "invalid_return"
        assert report["reason"] == "banked_return_at_or_below_total_loss"
        assert report["monthly_return_percent"] is None
