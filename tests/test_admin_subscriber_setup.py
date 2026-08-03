import os

os.environ.setdefault("JWT_SECRET_KEY", "test-admin-secret-" + "x" * 64)
os.environ.setdefault("SUBSCRIBER_JWT_SECRET_KEY", "test-subscriber-secret-" + "y" * 64)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.copytrading.models import CopySubscriber
from api.copytrading import routes as copy_routes
from api.database import Base, get_db
from api.subscriber_invites.models import SubscriberInvite
from api.subscriber_invites import routes as invite_routes


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine, tables=[CopySubscriber.__table__, SubscriberInvite.__table__])


def override_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(copy_routes.router, prefix="/copytrading")
app.include_router(invite_routes.router)
app.dependency_overrides[get_db] = override_db
app.dependency_overrides[copy_routes.require_admin] = lambda: {"role": "super_admin"}
client = TestClient(app)


def test_admin_creation_is_idempotent_and_invite_survives_email_failure(monkeypatch):
    payload = {"name": "Adam Abu", "email": "yaatuni33@gmail.com", "account_number": "49224282", "allocation_percent": 100}
    first = client.post("/copytrading/subscribers", json=payload)
    second = client.post("/copytrading/subscribers", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    monkeypatch.setattr(invite_routes, "record_and_send", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("email unavailable")))
    invited = client.post(f"/admin/subscribers/{first.json()['id']}/invite", json={})
    assert invited.status_code == 200
    assert invited.json()["setup_url"].startswith("http://testserver/investor-frontend/setup-password.html?token=")
    assert invited.json()["email_status"] == "FAILED"
