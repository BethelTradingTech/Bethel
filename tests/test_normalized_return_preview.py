from datetime import datetime

from api.services.normalized_return_preview import count_weekdays_inclusive


def test_counts_fxblue_account_history_weekdays_inclusively():
    start = datetime(2026, 7, 10, 0, 3, 3)
    end = datetime(2026, 8, 5, 17, 18, 9)

    assert count_weekdays_inclusive(start, end) == 19


def test_weekend_dates_do_not_inflate_trading_day_count():
    start = datetime(2026, 8, 1, 9, 0)  # Saturday
    end = datetime(2026, 8, 3, 17, 0)   # Monday

    assert count_weekdays_inclusive(start, end) == 1


def test_same_weekday_counts_as_one_trading_day():
    start = datetime(2026, 8, 5, 9, 0)
    end = datetime(2026, 8, 5, 17, 0)

    assert count_weekdays_inclusive(start, end) == 1


def test_reversed_history_boundaries_return_zero():
    start = datetime(2026, 8, 5, 17, 0)
    end = datetime(2026, 8, 4, 17, 0)

    assert count_weekdays_inclusive(start, end) == 0
