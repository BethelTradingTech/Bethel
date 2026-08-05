from pathlib import Path


def test_copyhub_frontend_uses_backend_derived_statuses():
    source = Path("admin-frontend/js/admin-control.js").read_text(encoding="utf-8")
    assert "row.connection_status" in source
    assert "row.copy_status" in source
    assert "Date.now()-heartbeat.getTime()" not in source
    assert 'row.active?"ACTIVE":"INACTIVE"' not in source


def test_copyhub_backend_exposes_dynamic_status_fields():
    source = Path("api/copyhub/routes.py").read_text(encoding="utf-8")
    for field in ("operational_status", "connection_status", "copy_status", "can_activate", "can_pause", "can_resume"):
        assert field in source
