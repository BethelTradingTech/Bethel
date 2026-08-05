from api.services import analytics_comparison as comparison


def _candidate(return_status="available", risk_status="available"):
    return {
        "status": "success",
        "master_account": "12345",
        "return_analytics": {
            "status": return_status,
            "since_inception_return_percent": 12.5,
            "rolling_1d_return_percent": 0.5,
            "rolling_1w_return_percent": 3.2,
            "rolling_1m_return_percent": 11.8,
        },
        "risk_analytics": {
            "status": risk_status,
            "required_exposed_days": 45,
            "available_exposed_days": 45 if risk_status == "available" else 20,
            "monthly_var_95_percent": 5.1 if risk_status == "available" else None,
            "monthly_expected_shortfall_95_percent": 7.0 if risk_status == "available" else None,
        },
    }


def _stable(account="12345"):
    return {
        "status": "success",
        "master_account": account,
        "total_return_percent": 10.0,
        "daily_return_percent": 0.4,
        "weekly_return_percent": 2.9,
        "monthly_return_percent": 10.2,
    }


def test_numeric_delta_is_candidate_minus_stable():
    assert comparison._numeric_delta(12.5, 10.0) == 2.5
    assert comparison._numeric_delta(None, 10.0) is None


def test_comparison_blocks_merge_on_account_mismatch(monkeypatch):
    monkeypatch.setattr(comparison, "get_performance_analytics", lambda: _stable("99999"))
    monkeypatch.setattr(comparison, "get_audited_analytics", lambda account: _candidate())
    monkeypatch.setattr(comparison, "_quality_report", lambda account: {"status": "pass"})

    report = comparison.get_analytics_comparison("12345")

    assert report["status"] == "account_mismatch"
    assert report["same_account"] is False
    assert report["merge_ready"] is False


def test_comparison_blocks_merge_when_risk_history_is_insufficient(monkeypatch):
    monkeypatch.setattr(comparison, "get_performance_analytics", lambda: _stable())
    monkeypatch.setattr(
        comparison,
        "get_audited_analytics",
        lambda account: _candidate(risk_status="insufficient_history"),
    )
    monkeypatch.setattr(comparison, "_quality_report", lambda account: {"status": "pass"})

    report = comparison.get_analytics_comparison("12345")

    assert report["status"] == "success"
    assert report["risk_readiness"]["available_exposed_days"] == 20
    assert report["merge_ready"] is False


def test_comparison_marks_merge_ready_only_when_all_gates_pass(monkeypatch):
    monkeypatch.setattr(comparison, "get_performance_analytics", lambda: _stable())
    monkeypatch.setattr(comparison, "get_audited_analytics", lambda account: _candidate())
    monkeypatch.setattr(comparison, "_quality_report", lambda account: {"status": "pass"})

    report = comparison.get_analytics_comparison("12345")

    assert report["status"] == "success"
    assert report["return_comparison"]["since_inception_delta_percentage_points"] == 2.5
    assert report["merge_ready"] is True


def test_comparison_blocks_merge_when_data_quality_requires_review(monkeypatch):
    monkeypatch.setattr(comparison, "get_performance_analytics", lambda: _stable())
    monkeypatch.setattr(comparison, "get_audited_analytics", lambda account: _candidate())
    monkeypatch.setattr(
        comparison,
        "_quality_report",
        lambda account: {"status": "review_required", "issues": ["snapshot_gap_over_72_hours"]},
    )

    report = comparison.get_analytics_comparison("12345")

    assert report["data_quality"]["status"] == "review_required"
    assert report["merge_ready"] is False
