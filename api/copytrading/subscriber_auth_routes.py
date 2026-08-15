"""
Bethel Trading Technologies

Subscriber Authentication API

Handles:
- Public subscriber registration
- Subscriber email verification
- Subscriber login
- Password reset
- JWT token generation
- Hardened subscriber session cookie and logout

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

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from api.database import SessionLocal
from api.copytrading.email_verification import SubscriberEmailVerification
from api.copytrading.password_reset import SubscriberPasswordReset
from api.copytrading.models import CopySubscriber
from api.auth.rate_limit import (
    check_login_allowed,
    check_registration_allowed,
    clear_login_failures,
    record_login_failure,
)
from api.notifications.emailer import portal_url, record_and_send
from api.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    hash_password,
    verify_password,
    create_access_token,
)


router = APIRouter(
    prefix="/copytrading/auth",
    tags=["Subscriber Authentication"],
)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=12, max_length=128)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _password_is_strong(password: str) -> bool:
    return all(
        (
            any(ch.islower() for ch in password),
            any(ch.isupper() for ch in password),
            any(ch.isdigit() for ch in password),
            any(ch in string.punctuation for ch in password),
        )
    )


def _ensure_verification_table(db) -> None:
    SubscriberEmailVerification.__table__.create(bind=db.get_bind(), checkfirst=True)


def _ensure_password_reset_table(db) -> None:
    SubscriberPasswordReset.__table__.create(bind=db.get_bind(), checkfirst=True)


def _verification_lifetime_hours() -> int:
    try:
        return max(1, min(int(os.getenv("EMAIL_VERIFICATION_HOURS", "24")), 168))
    except ValueError:
        return 24


def _password_reset_lifetime_minutes() -> int:
    try:
        return max(10, min(int(os.getenv("PASSWORD_RESET_MINUTES", "60")), 1440))
    except ValueError:
        return 60


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


def _create_password_reset(db, subscriber: CopySubscriber) -> str:
    _ensure_password_reset_table(db)
    raw_token = secrets.token_urlsafe(32)
    record = (
        db.query(SubscriberPasswordReset)
        .filter(SubscriberPasswordReset.subscriber_id == subscriber.id)
        .first()
    )
    expires_at = datetime.utcnow() + timedelta(minutes=_password_reset_lifetime_minutes())
    if record is None:
        record = SubscriberPasswordReset(
            subscriber_id=subscriber.id,
            token_hash=_token_hash(raw_token),
            expires_at=expires_at,
            used_at=None,
        )
        db.add(record)
    else:
        record.token_hash = _token_hash(raw_token)
        record.expires_at = expires_at
        record.used_at = None
        record.created_at = datetime.utcnow()
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


def _send_password_reset_email(db, subscriber: CopySubscriber, raw_token: str) -> None:
    reset_url = portal_url(f"reset-password.html?token={raw_token}")
    record_and_send(
        db,
        recipient=subscriber.email,
        subscriber_id=subscriber.id,
        message_type="SUBSCRIBER_PASSWORD_RESET",
        subject="Reset your Bethel Trading Technologies password",
        text_body=(
            f"Hello {subscriber.name},\n\n"
            "We received a request to reset your Bethel Trading Technologies password.\n\n"
            f"Reset your password: {reset_url}\n\n"
            f"This link expires in {_password_reset_lifetime_minutes()} minutes and can be used once. "
            "If you did not request a password reset, you can ignore this email and your current password will remain unchanged."
        ),
        deduplication_key=f"subscriber-password-reset:{subscriber.id}:{_token_hash(raw_token)[:16]}",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_subscriber_password(data: RegisterRequest, request: Request):
    if os.getenv("PUBLIC_SUBSCRIBER_REGISTRATION_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=503, detail="Public registration is temporarily unavailable")
    check_registration_allowed(request)
    if not _password_is_strong(data.password):
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


@router.post("/forgot-password")
def forgot_subscriber_password(data: ForgotPasswordRequest, request: Request):
    check_registration_allowed(request)
    generic = {
        "status": "success",
        "message": "If an account exists for that email, a secure password reset link has been sent.",
    }
    db = SessionLocal()
    try:
        email = str(data.email).strip().lower()
        subscriber = db.query(CopySubscriber).filter(func.lower(CopySubscriber.email) == email).first()
        if subscriber is None or not subscriber.password_hash:
            return generic
        raw_token = _create_password_reset(db, subscriber)
        _send_password_reset_email(db, subscriber, raw_token)
        db.commit()
        return generic
    finally:
        db.close()


@router.post("/reset-password")
def reset_subscriber_password(data: ResetPasswordRequest):
    if not _password_is_strong(data.password):
        raise HTTPException(
            status_code=422,
            detail="Password must contain uppercase, lowercase, number, and special characters",
        )

    db = SessionLocal()
    try:
        _ensure_password_reset_table(db)
        record = (
            db.query(SubscriberPasswordReset)
            .filter(SubscriberPasswordReset.token_hash == _token_hash(data.token))
            .first()
        )
        if record is None or record.used_at is not None:
            raise HTTPException(status_code=400, detail="Invalid or already used password reset link")
        if record.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Password reset link has expired")
        subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == record.subscriber_id).first()
        if subscriber is None:
            raise HTTPException(status_code=400, detail="Invalid password reset link")
        subscriber.password_hash = hash_password(data.password)
        record.used_at = datetime.utcnow()
        db.commit()
        return {
            "status": "success",
            "message": "Password reset successfully. You can now sign in with your new password.",
        }
    finally:
        db.close()


@router.post("/login")
def subscriber_login(data: LoginRequest, request: Request, response: Response):
    email = str(data.email).strip().lower()
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
        response.set_cookie(
            key="subscriber_access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
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


@router.post("/logout")
def subscriber_logout(response: Response):
    response.delete_cookie(
        key="subscriber_access_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return {"status": "success", "message": "Logged out"}
