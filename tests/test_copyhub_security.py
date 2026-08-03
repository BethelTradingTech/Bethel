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

from api.broker_accounts.models import BrokerAccount
from api.copyhub.models import CopyChannel, CopyDelivery, CopyEvent, CopyReceiver, ReceiverActivation
from api.copyhub import routes
from api.copytrading.models import CopySubscriber
from api.database import Base, get_db
from api.mt5_ingest.models import ConnectorNonce
from api.subscription_lifecycle.models import SubscriptionLifecycle


SECRET = "s" * 64
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(engine, tables=[
    CopySubscriber.__table__, BrokerAccount.__table__, SubscriptionLifecycle.__table__,
    ConnectorNonce.__table__, CopyChannel.__table__, CopyReceiver.__table__,
    CopyEvent.__table__, CopyDelivery.__table__,
    ReceiverActivation.__table__,
])


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(routes.router)
app.dependency_overrides[get_db] = override_db
app.dependency_overrides[routes.require_super_admin] = lambda: {"role": "super_admin"}
client = TestClient(app)


def signed_event(event_key="master:1:open"):
    payload = {"account_number": "49617874", "event_key": event_key, "master_ticket": "1", "event_type": "OPEN", "symbol": "EURUSD", "direction": "BUY", "volume": 0.1, "price": 1.1}
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    nonce = "copyhub-event-nonce-" + event_key.replace(":", "-")
    signature = hmac.new(SECRET.encode(), timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body, hashlib.sha256).hexdigest()
    return client.post("/copyhub/v1/master/events", content=body, headers={"Content-Type": "application/json", "X-Bethel-Connector-Id": "owner-laptop-1", "X-Bethel-Timestamp": timestamp, "X-Bethel-Nonce": nonce, "X-Bethel-Signature": signature})


def test_master_event_requires_signature(monkeypatch):
    monkeypatch.setenv("MT5_CONNECTOR_SECRET", SECRET)
    assert client.post("/copyhub/v1/master/events", json={}).status_code == 401
    assert signed_event().status_code == 202


def test_usd_usc_metadata_must_be_consistent():
    db = TestingSession()
    subscriber = CopySubscriber(name="Owner follower", email="owner@example.test", mt5_account="49224282", status="ACTIVE")
    db.add(subscriber); db.flush()
    account = BrokerAccount(subscriber_id=subscriber.id, broker="HFM", platform="MT5", login="49224282", server="HFMGLOBALMARKETS-DEMO", status="CONNECTED", currency="USD")
    db.add(account); db.commit()
    response = client.post("/copyhub/v1/admin/receivers", json={"subscriber_id": subscriber.id, "broker_account_id": account.id, "environment": "DEMO", "currency_unit": "USD", "is_cent_account": True})
    assert response.status_code == 422
    db.close()


def test_activation_code_is_one_time_and_account_bound():
    db = TestingSession()
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.mt5_account == "49224282").first()
    account = db.query(BrokerAccount).filter(BrokerAccount.login == "49224282").first()
    provision = client.post("/copyhub/v1/admin/receivers", json={"subscriber_id": subscriber.id, "broker_account_id": account.id, "environment": "DEMO", "currency_unit": "USD", "is_cent_account": False, "contract_size": 100000, "min_lot": 0.01, "max_lot": 100, "lot_step": 0.01})
    assert provision.status_code == 201
    code = provision.json()["activation_code"]
    payload = {"activation_code": code, "account_number": "99999999", "environment": "DEMO", "currency_unit": "USD", "is_cent_account": False, "contract_size": 100000, "min_lot": 0.01, "max_lot": 100, "lot_step": 0.01}
    assert client.post("/copyhub/v1/receiver/activate", json=payload).status_code == 409
    payload["account_number"] = "49224282"
    accepted = client.post("/copyhub/v1/receiver/activate", json=payload)
    assert accepted.status_code == 200
    assert len(accepted.json()["receiver_token"]) >= 48
    db.expire_all()
    assert db.query(BrokerAccount).filter(BrokerAccount.id == account.id).one().status == "CONNECTED"
    assert client.post("/copyhub/v1/receiver/activate", json=payload).status_code == 401
    db.close()
