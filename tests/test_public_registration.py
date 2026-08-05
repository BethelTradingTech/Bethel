import os

os.environ.setdefault("SUBSCRIBER_JWT_SECRET_KEY", "test-subscriber-secret-" + "x" * 64)
os.environ.setdefault("JWT_SECRET_KEY", "test-admin-secret-" + "y" * 64)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.copytrading.email_verification import SubscriberEmailVerification
from api.copytrading.models import CopySubscriber
from api.copytrading import subscriber_auth_routes
from api.database import Base, get_db
from api.notifications.models import EmailDelivery
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.onboarding import routes as onboarding_routes


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(
    engine,
    tables=[
        CopySubscriber.__table__,
        SubscriberEmailVerification.__table__,
        EmailDelivery.__table__,
        SubscriptionPlan.__table__,
        ClientOnboarding.__table__,
    ],
)


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


def test_public_registration_requires_email_verification(monkeypatch):
    monkeypatch.setattr(subscriber_auth_routes, "SessionLocal", Session)
    sent_tokens = []

    def capture_email(db, subscriber, raw_token):
        sent_tokens.append(raw_token)

    monkeypatch.setattr(subscriber_auth_routes, "_send_verification_email", capture_email)
    payload = {
        "name": "Public Subscriber",
        "email": "PUBLIC@example.com",
        "password": "SecurePassword123!",
    }
    created = client.post("/copytrading/auth/register", json=payload)
    assert created.status_code == 201
    assert created.json()["subscriber_id"] > 0
    assert created.json()["email_verified"] is False
    assert len(sent_tokens) == 1

    duplicate = client.post("/copytrading/auth/register", json=payload)
    assert duplicate.status_code == 409

    blocked = client.post(
        "/copytrading/auth/login",
        json={"email": "PUBLIC@EXAMPLE.COM", "password": payload["password"]},
    )
    assert blocked.status_code == 403
    assert "Verify your email" in blocked.json()["detail"]

    verified = client.get(
        "/copytrading/auth/verify-email",
        params={"token": sent_tokens[0]},
    )
    assert verified.status_code == 200
    assert verified.json()["email_verified"] is True

    logged_in = client.post(
        "/copytrading/auth/login",
        json={"email": "PUBLIC@EXAMPLE.COM", "password": payload["password"]},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["access_token"]
    assert logged_in.json()["email_verified"] is True


def test_default_100_usd_plan_is_available():
    response = client.get("/onboarding/plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 1
    assert plans[0]["price"] == 100.0
    assert plans[0]["currency"] == "USD"
