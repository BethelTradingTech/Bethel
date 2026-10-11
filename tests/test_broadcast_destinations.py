import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text

from api.broadcast.migrations import ensure_x_column


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("BROADCAST_WORKER_SECRET", "s" * 64)
    path = Path(__file__).parents[1] / "broadcast-worker" / "app.py"
    spec = importlib.util.spec_from_file_location("broadcast_worker_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_existing_control_migration_preserves_disabled_default():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE broadcast_control (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO broadcast_control (id) VALUES (1)"))
    ensure_x_column(engine)
    ensure_x_column(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT x_enabled FROM broadcast_control")).scalar() == 0


def test_x_is_landscape_and_requires_opt_in(worker, monkeypatch):
    monkeypatch.setitem(worker.SOCIAL_URLS, "x", "rtmps://example.com/live/secret")
    assert worker.L.wanted({"destinations": {"x": True}}) == (("x", "rtmps://example.com/live/secret"),)
    assert worker.V.wanted({"destinations": {"x": True}}) == ()
    assert worker.L.wanted({"destinations": {"x": False}}) == ()


def test_readiness_is_private_and_does_not_return_credentials(worker, monkeypatch):
    monkeypatch.setitem(worker.SOCIAL_URLS, "x", "rtmps://example.com/live/private-key")
    with pytest.raises(HTTPException) as error:
        worker.destination_status("")
    assert error.value.status_code == 401
    response = worker.destination_status("s" * 64)
    assert response["destinations"]["x"]["configured"] is True
    assert "private-key" not in str(response)
    monkeypatch.setitem(worker.SOCIAL_URLS, "x", "")
    assert worker.destination_status("s" * 64)["destinations"]["x"]["configured"] is False
