"""
Bethel Trading Technologies

Subscriber Authentication API

Handles:
- Public subscriber registration
- Subscriber email verification
- Subscriber login
- JWT token generation

Does NOT:
- Handle payments
- Execute trades
- Manage funds
"""

from datetime import datetime, timedelta
import hashlib
import os
import secrets
import string

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from api.database import SessionLocal
from api.copytrading.email_verification import SubscriberEmailVerification
from api.copytrading.models import CopySubscriber
from api.auth.rate_limit import (
    check_login_allowed,
    check_registration_allowed,
    clear_login_failures,
    record_login_failure,
)
from api.notifications.emailer import portal_url, record_and_send
from api.security import hash_password, verify_password, create_access_token


router = APIRouter(
    prefix="/copytrading/auth",
    tags=["Subscriber Authentication"],
)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ensure_verification_table(db) -> None:
    SubscriberEmailVerification.__table__.create(bind=db.get_bind(), checkfirst=True)


def _verification_lifetime_hours() -> int:
    try:
        return max(1, min(int(os.getenv("EMAIL_VERIFICATION_HOURS", "24")), 168))
    except ValueError:
        return 24


def _create_verification(db, subscriber: CopySubscriber) -> str:
    _ensure_verification_table(db)
    raw_token = secrets.token_urlsafe(32)
    record = (
        db.query(SubscriberEmailVerification)
        .filter(SubscriberEmailVerification.subscriber_id == subscriber.id)
        .first()
    )
    if record is None:
        record = SubscriberEmailVerification(
            subscriber_id=subscriber.id,
            token_hash=_token_hash(raw_token),
            expires_at=datetime.utcnow() + timedelta(hours=_verification_lifetime_hours()),
        )
        db.add(record)
    else:
        record.token_hash = _token_hash(raw_token)
        record.expires_at = datetime.utcnow() + timedelta(hours=_verification_lifetime_hours())
        record.verified_at = None
    return raw_token


def _send_verification_email(db, subscriber: CopySubscriber, raw_token: str) -> None:
    verification_url = portal_url(f"verify-email.html?token={raw_token}")
    record_and_send(
        db,
        recipient=subscriber.email,
        subscriber_id=subscriber.id,
        message_type="SUBSCRIBER_EMAIL_VERIFICATION",
        subject="Verify your Bethel subscriber email",
        text_body=(
            f"Hello {subscriber.name},\n\n"
            "Verify your email address before continuing your Bethel subscriber onboarding.\n\n"
            f"Verification link: {verification_url}\n\n"
            f"This link expires in {_verification_lifetime_hours()} hours. "
            "If you did not register, ignore this message."
        ),
        deduplication_key=f"subscriber-email-verification:{subscriber.id}:{_token_hash(raw_token)[:16]}",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_subscriber_password(data: RegisterRequest, request: Request):
    if os.getenv("PUBLIC_SUBSCRIBER_REGISTRATION_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=503, detail="Public registration is temporarily unavailable")
    check_registration_allowed(request)
    checks = (
        any(ch.islower() for ch in data.password),
        any(ch.isupper() for ch in data.password),
        any(ch.isdigit() for ch in data.password),
        any(ch in string.punctuation for ch in data.password),
    )
    if not all(checks):
        raise HTTPException(
            status_code=422,
            detail="Password must contain uppercase, lowercase, number, and special characters",
        )

    db = SessionLocal()
    try:
        email = str(data.email).strip().lower()
        existing = db.query(CopySubscriber).filter(func.lower(CopySubscriber.email) == email).first()
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        subscriber = CopySubscriber(
            name=data.name.strip(),
            email=email,
            password_hash=hash_password(data.password),
            mt5_account=f"PENDING-{secrets.token_hex(12)}",
            allocation_percent=100.0,
            status="EMAIL_UNVERIFIED",
            payment_status="UNPAID",
        )
        db.add(subscriber)
        db.flush()
        raw_token = _create_verification(db, subscriber)
        _send_verification_email(db, subscriber, raw_token)
        db.commit()
        db.refresh(subscriber)
        return {
            "status": "success",
            "subscriber_id": subscriber.id,
            "email_verified": False,
            "message": "Account created. Check your email and verify it before signing in.",
        }
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Subscriber account already exists") from exc
    finally:
        db.close()


@router.get("/verify-email")
def verify_subscriber_email(
    token: str = Query(..., min_length=20, max_length=200),
):
    db = SessionLocal()
    try:
        _ensure_verification_table(db)
        record = (
            db.query(SubscriberEmailVerification)
            .filter(SubscriberEmailVerification.token_hash == _token_hash(token))
            .first()
        )
        if record is None:
            raise HTTPException(status_code=400, detail="Invalid verification link")
        if record.verified_at is not None:
            return {"status": "success", "email_verified": True, "message": "Email is already verified."}
        if record.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Verification link has expired")
        subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == record.subscriber_id).first()
        if subscriber is None:
            raise HTTPException(status_code=404, detail="Subscriber account not found")
        record.verified_at = datetime.utcnow()
        if subscriber.status == "EMAIL_UNVERIFIED":
            subscriber.status = "PENDING"
        db.commit()
        return {"status": "success", "email_verified": True, "message": "Email verified. You may now sign in."}
    finally:
        db.close()


@router.post("/resend-verification")
def resend_subscriber_verification(data: ResendVerificationRequest, request: Request):
    check_registration_allowed(request)
    db = SessionLocal()
    try:
        email = str(data.email).strip().lower()
        subscriber = db.query(CopySubscriber).filter(func.lower(CopySubscriber.email) == email).first()
        generic = {"status": "success", "message": "If the account requires verification, a new email has been sent."}
        if subscriber is None:
            return generic
        _ensure_verification_table(db)
        existing = (
            db.query(SubscriberEmailVerification)
            .filter(SubscriberEmailVerification.subscriber_id == subscriber.id)
            .first()
        )
        if existing is not None and existing.verified_at is not None:
            return generic
        raw_token = _create_verification(db, subscriber)
        _send_verification_email(db, subscriber, raw_token)
        db.commit()
        return generic
    finally:
        db.close()


@router.post("/login")
def subscriber_login(data: LoginRequest, request: Request):
    email = data.email.strip().lower()
    check_login_allowed(request, email)
    db = SessionLocal()
    try:
        subscriber = (
            db.query(CopySubscriber)
            .filter(func.lower(CopySubscriber.email) == email)
            .first()
        )
        if not subscriber or not subscriber.password_hash:
            record_login_failure(request, email)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not verify_password(data.password, subscriber.password_hash):
            record_login_failure(request, email)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        _ensure_verification_table(db)
        verification = (
            db.query(SubscriberEmailVerification)
            .filter(SubscriberEmailVerification.subscriber_id == subscriber.id)
            .first()
        )
        if verification is not None and verification.verified_at is None:
            raise HTTPException(status_code=403, detail="Verify your email address before signing in")

        clear_login_failures(request, email)
        token = create_access_token({"subscriber_id": subscriber.id})
        return {
            "status": "success",
            "access_token": token,
            "token_type": "bearer",
            "subscriber_id": subscriber.id,
            "name": subscriber.name,
            "email_verified": verification is None or verification.verified_at is not None,
        }
    finally:
        db.close()
