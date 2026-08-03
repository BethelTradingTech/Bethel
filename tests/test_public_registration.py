import os

os.environ.setdefault("SUBSCRIBER_JWT_SECRET_KEY", "test-subscriber-secret-" + "x" * 64)
os.environ.setdefault("JWT_SECRET_KEY", "test-admin-secret-" + "y" * 64)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.copytrading.models import CopySubscriber
from api.copytrading import subscriber_auth_routes
from api.database import Base, get_db
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding import routes as onboarding_routes


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine, tables=[CopySubscriber.__table__, SubscriptionPlan.__table__, ClientOnboarding.__table__])


def override_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(subscriber_auth_routes.router)
app.include_router(onboarding_routes.router)
app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def test_public_registration_and_login(monkeypatch):
    monkeypatch.setattr(subscriber_auth_routes, "SessionLocal", Session)
    payload = {"name": "Public Subscriber", "email": "PUBLIC@example.com", "password": "SecurePassword123!"}
    created = client.post("/copytrading/auth/register", json=payload)
    assert created.status_code == 201
    assert created.json()["subscriber_id"] > 0
    duplicate = client.post("/copytrading/auth/register", json=payload)
    assert duplicate.status_code == 409
    logged_in = client.post("/copytrading/auth/login", json={"email": "public@example.com", "password": payload["password"]})
    assert logged_in.status_code == 200
    assert logged_in.json()["access_token"]


def test_default_100_usd_plan_is_available():
    response = client.get("/onboarding/plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 1
    assert plans[0]["price"] == 100.0
    assert plans[0]["currency"] == "USD"
