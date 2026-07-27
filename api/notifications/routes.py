from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.notifications.emailer import portal_url, record_and_send, smtp_configured
from api.notifications.models import EmailDelivery, PasswordReset
from api.notifications.service import (
    queue_renewal_reminders,
    synchronize_status_notifications,
)
from api.security import hash_password
from api.subscriber_invites.routes import validate_password


router = APIRouter(tags=["Email Notifications"])


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=200)
    password: str = Field(min_length=12, max_length=128)


class NotificationRequest(BaseModel):
    subscriber_id: int
    subject: str = Field(min_length=3, max_length=255)
    message: str = Field(min_length=3, max_length=5000)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/copytrading/auth/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.email == data.email)
        .first()
    )
    generic = {
        "status": "accepted",
        "message": "If the account exists, a password-reset email has been sent.",
    }
    if subscriber is None or not subscriber.password_hash:
        return generic

    now = datetime.utcnow()
    previous = (
        db.query(PasswordReset)
        .filter(
            PasswordReset.subscriber_id == subscriber.id,
            PasswordReset.used_at.is_(None),
        )
        .all()
    )
    for reset in previous:
        reset.used_at = now
    raw_token = secrets.token_urlsafe(32)
    db.add(PasswordReset(
        subscriber_id=subscriber.id,
        token_hash=digest(raw_token),
        expires_at=now + timedelta(minutes=30),
    ))
    reset_url = portal_url(
        f"reset-password.html?token={raw_token}"
    )
    record_and_send(
        db,
        recipient=subscriber.email,
        subscriber_id=subscriber.id,
        message_type="PASSWORD_RESET",
        subject="Reset your Bethel subscriber password",
        text_body=(
            f"Hello {subscriber.name},\n\n"
            "Use this one-time link to reset your password. "
            "It expires in 30 minutes:\n"
            f"{reset_url}\n\n"
            "If you did not request this, ignore this message."
        ),
    )
    db.commit()
    return generic


@router.post("/copytrading/auth/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    validate_password(data.password)
    now = datetime.utcnow()
    reset = (
        db.query(PasswordReset)
        .filter(
            PasswordReset.token_hash == digest(data.token),
            PasswordReset.used_at.is_(None),
        )
        .first()
    )
    if reset is None or reset.expires_at <= now:
        raise HTTPException(
            status_code=400,
            detail="Reset link is invalid, expired, or already used",
        )
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == reset.subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    subscriber.password_hash = hash_password(data.password)
    reset.used_at = now
    db.commit()
    return {"status": "success", "message": "Password reset successfully"}


@router.get("/admin/notifications")
def list_notifications(
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    rows = (
        db.query(EmailDelivery)
        .order_by(EmailDelivery.id.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return {
        "smtp_configured": smtp_configured(),
        "deliveries": [
            {
                "id": row.id,
                "subscriber_id": row.subscriber_id,
                "recipient": row.recipient,
                "message_type": row.message_type,
                "subject": row.subject,
                "status": row.status,
                "attempts": row.attempts,
                "error": row.error,
                "created_at": row.created_at.isoformat(),
                "sent_at": row.sent_at.isoformat() if row.sent_at else None,
            }
            for row in rows
        ],
    }


@router.post("/admin/notifications/send")
def send_notification(
    data: NotificationRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == data.subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    delivery = record_and_send(
        db,
        recipient=subscriber.email,
        subscriber_id=subscriber.id,
        message_type="ADMIN_MESSAGE",
        subject=data.subject,
        text_body=data.message,
    )
    db.commit()
    return {"status": delivery.status, "delivery_id": delivery.id}


@router.post("/admin/notifications/synchronize")
def synchronize_notifications(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    status_result = synchronize_status_notifications(db)
    reminder_result = queue_renewal_reminders(db)
    db.commit()
    return {
        "status": "success",
        **status_result,
        **reminder_result,
        "smtp_configured": smtp_configured(),
    }
