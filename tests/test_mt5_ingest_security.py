from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import time

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-" + "x" * 64)
os.environ.setdefault("SUBSCRIBER_JWT_SECRET_KEY", "test-subscriber-secret-" + "y" * 64)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorDeal, ConnectorNonce, ConnectorPosition, ConnectorStatus
from api.mt5_ingest import routes


SECRET = "s" * 64
ACCOUNT = "49617874"


def setup_module():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[EquitySnapshot.__table__, ConnectorNonce.__table__, ConnectorStatus.__table__, ConnectorPosition.__table__, ConnectorDeal.__table__])
    routes.SessionLocal = sessionmaker(bind=engine)


app = FastAPI()
app.include_router(routes.router)
app.dependency_overrides[routes.require_admin] = lambda: {"role": "super_admin"}
client = TestClient(app)


def signed_request(monkeypatch, payload=None, nonce="abcdefghijklmnopqrstuvwxyz123456"):
    monkeypatch.setenv("MT5_CONNECTOR_SECRET", SECRET)
    monkeypatch.setenv("MASTER_MT5_ACCOUNTS", ACCOUNT)
    monkeypatch.setenv("MASTER_ACCOUNT_MODE", "DEMO")
    payload = payload or {
        "account_number": ACCOUNT,
        "server": "HFMGlobalMarkets-Demo",
        "currency": "USD",
        "balance": 10000,
        "equity": 10025,
        "floating_profit": 25,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "mode": "DEMO",
        "positions": [{
            "ticket": "123456", "symbol": "EURUSD", "direction": "BUY", "volume": 0.1,
            "open_price": 1.1, "current_price": 1.101, "stop_loss": 1.09,
            "take_profit": 1.12, "profit": 10.0, "swap": 0.0,
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }],
        "closed_deals": [{
            "deal_ticket": "654321", "position_id": "555", "order_id": "777",
            "symbol": "EURUSD", "deal_type": "SELL", "volume": 0.1, "price": 1.101,
            "profit": 10.0, "commission": -0.5, "swap": -0.1, "fee": 0,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }],
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        SECRET.encode(), timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body, hashlib.sha256
    ).hexdigest()
    return client.post("/connector/v1/snapshot", content=body, headers={
        "Content-Type": "application/json",
        "X-Bethel-Connector-Id": "owner-laptop-1",
        "X-Bethel-Timestamp": timestamp,
        "X-Bethel-Nonce": nonce,
        "X-Bethel-Signature": signature,
    })


def test_valid_signed_snapshot_is_accepted(monkeypatch):
    response = signed_request(monkeypatch)
    assert response.status_code == 202
    assert response.json() == {"status": "accepted", "read_only": True}
    status = client.get("/connector/v1/status")
    assert status.status_code == 200
    assert status.json()["connectors"][0]["account_number"] == ACCOUNT
    assert status.json()["connectors"][0]["read_only"] is True
    assert status.json()["connectors"][0]["open_position_count"] == 1
    assert status.json()["connectors"][0]["open_positions"][0]["ticket"] == "123456"
    assert signed_request(monkeypatch, nonce="dedupe-deal-ticket-abcdefghijklmnop").status_code == 202
    db = routes.SessionLocal()
    try:
        assert db.query(ConnectorDeal).filter(ConnectorDeal.deal_ticket == "654321").count() == 1
    finally:
        db.close()


def test_replayed_nonce_is_rejected(monkeypatch):
    nonce = "unique-replay-nonce-abcdefghijklmnopqrstuvwxyz"
    assert signed_request(monkeypatch, nonce=nonce).status_code == 202
    assert signed_request(monkeypatch, nonce=nonce).status_code == 409


def test_wrong_account_and_mode_are_rejected(monkeypatch):
    bad_account = {
        "account_number": "49224282", "server": "HFMGlobalMarkets-Demo", "currency": "USD",
        "balance": 100, "equity": 100, "floating_profit": 0,
        "observed_at": datetime.now(timezone.utc).isoformat(), "mode": "DEMO",
    }
    assert signed_request(monkeypatch, bad_account, "wrong-account-nonce-abcdefghij").status_code == 403
    bad_account["account_number"] = ACCOUNT
    bad_account["mode"] = "LIVE"
    assert signed_request(monkeypatch, bad_account, "wrong-mode-nonce-abcdefghijkl").status_code == 403


def test_unsigned_request_is_rejected(monkeypatch):
    monkeypatch.setenv("MT5_CONNECTOR_SECRET", SECRET)
    assert client.post("/connector/v1/snapshot", json={}).status_code == 401
