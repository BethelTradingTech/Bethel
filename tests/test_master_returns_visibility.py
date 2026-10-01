"""Regression tests for return visibility, without database or authentication."""
import ast
from datetime import datetime, timezone
from pathlib import Path

def report(profile=None, error=False, finalized_profile=None):
    source = ast.parse(Path("api/admin_master_performance.py").read_text())
    function = next(node for node in source.body if isinstance(node, ast.FunctionDef)
                    and node.name == "_profile_return_report")
    def get_profile(account, as_of=None):
        assert account == "12345"
        if error:
            raise RuntimeError("test failure")
        if as_of is not None:
            assert as_of == datetime(2026, 10, 1)
            return finalized_profile
        return profile
    namespace = {"datetime": datetime, "timezone": timezone,
                 "get_account_risk_profile": get_profile}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<returns>", "exec"), namespace)
    return namespace["_profile_return_report"]

def test_september_is_provisional_then_finalized_at_utc_rollover():
    calculate = report({"status": "available", "monthly_returns": [
        {"period": "2026-08", "return_percent": 1.25},
        {"period": "2026-09", "return_percent": -2.5}]})
    before = calculate(" 12345 ", now=datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc))
    assert before["monthly_returns"] == [{"month": "2026-08", "return_percent": 1.25}]
    assert before["provisional_monthly_returns"] == [{"month": "2026-09", "return_percent": -2.5}]
    after = calculate("12345", now=datetime(2026, 10, 1, tzinfo=timezone.utc))
    assert after["monthly_returns"][-1] == {"month": "2026-09", "return_percent": -2.5}
    assert after["provisional_monthly_returns"] == []

def test_reconciliation_failure_is_visible_and_has_no_fabricated_returns():
    result = report({"status": "not_available", "reason": "signed_ledger_reconciliation_failed"})("12345")
    assert result["status"] == "not_available"
    assert result["reason"] == "signed_ledger_reconciliation_failed"
    assert result["monthly_returns"] == result["provisional_monthly_returns"] == []

def test_exception_has_explicit_error_status():
    result = report(error=True)("12345")
    assert result["status"] == "error"
    assert result["reason"] == "calculation_failed"

def test_current_month_only_is_distinguished_from_history_failure():
    result = report({"status": "available", "monthly_returns": [
        {"period": "2026-09", "return_percent": 0}]})(
            "12345", now=datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert result["status"] == "available"
    assert result["reason"] == "no_finalized_months"
    assert result["provisional_monthly_returns"][0]["return_percent"] == 0

def test_invalid_and_future_rows_are_excluded():
    rows = [None, {"period": "2026-99", "return_percent": 1},
            {"period": "2026-08", "return_percent": float("nan")},
            {"period": "2026-08", "return_percent": float("inf")},
            {"period": "2026-10", "return_percent": 5}]
    result = report({"status": "available", "monthly_returns": rows})(
        "12345", now=datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert result["monthly_returns"] == result["provisional_monthly_returns"] == []

def test_october_adjustment_cannot_rewrite_finalized_september():
    september = {"status": "available", "history_end": "2026-09-30",
                 "raw_opening_balance": 0, "reconciliation_tolerance": 5,
                 "monthly_returns": [{"period": "2026-08", "return_percent": 2},
                                     {"period": "2026-09", "return_percent": -32.65}]}
    october = {"status": "available", "raw_opening_balance": 235.46,
               "reconciliation_tolerance": 6,
               "monthly_returns": [{"period": "2026-08", "return_percent": 8},
                                   {"period": "2026-09", "return_percent": -72.94},
                                   {"period": "2026-10", "return_percent": 1}]}
    result = report(october, finalized_profile=september)(
        "12345", now=datetime(2026, 10, 1, tzinfo=timezone.utc),
        lock_completed_months=True)
    assert result["monthly_returns"] == [
        {"month": "2026-08", "return_percent": 2},
        {"month": "2026-09", "return_percent": -32.65}]
    assert result["provisional_monthly_returns"] == []
    assert result["provisional_reason"] == "current_month_ledger_unreconciled"

def test_invalid_september_is_not_rescued_by_october_credit():
    september = {"status": "not_available", "reason": "invalid_signed_daily_return"}
    october = {"status": "available", "monthly_returns": [
        {"period": "2026-09", "return_percent": -72.94}]}
    result = report(october, finalized_profile=september)(
        "12345", now=datetime(2026, 10, 1, tzinfo=timezone.utc),
        lock_completed_months=True)
    assert result["monthly_returns"] == []
    assert result["reason"] == "invalid_signed_daily_return"

def test_missing_month_end_snapshot_does_not_finalise_partial_month():
    september = {"status": "available", "history_end": "2026-09-28",
                 "monthly_returns": [{"period": "2026-09", "return_percent": 10}]}
    result = report(september, finalized_profile=september)(
        "12345", now=datetime(2026, 10, 1, tzinfo=timezone.utc),
        lock_completed_months=True)
    assert result["monthly_returns"] == []
    assert result["reason"] == "month_end_snapshot_missing"
