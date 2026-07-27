from datetime import datetime, timedelta
import hashlib
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin
from api.copytrading.models import CopySubscriber
from api.security import hash_password
from api.database import get_db
from api.subscriber_invites.models import SubscriberInvite
from api.notifications.emailer import record_and_send


router = APIRouter(tags=["Subscriber Account Setup"])


class PasswordSetupRequest(BaseModel):
    token: str = Field(min_length=32, max_length=200)
    password: str = Field(min_length=12, max_length=128)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_password(password: str) -> None:
    checks = (
        any(ch.islower() for ch in password),
        any(ch.isupper() for ch in password),
        any(ch.isdigit() for ch in password),
        any(ch in string.punctuation for ch in password),
    )
    if not all(checks):
        raise HTTPException(
            status_code=422,
            detail=(
                "Password must contain uppercase, lowercase, number, "
                "and special characters"
            ),
        )


@router.post("/admin/subscribers/{subscriber_id}/invite")
def create_subscriber_invite(
    subscriber_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    now = datetime.utcnow()
    previous = (
        db.query(SubscriberInvite)
        .filter(
            SubscriberInvite.subscriber_id == subscriber_id,
            SubscriberInvite.used_at.is_(None),
        )
        .all()
    )
    for invite in previous:
        invite.used_at = now

    raw_token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(hours=24)
    db.add(
        SubscriberInvite(
            subscriber_id=subscriber_id,
            token_hash=token_digest(raw_token),
            expires_at=expires_at,
        )
    )
    db.commit()

    base = str(request.base_url).rstrip("/")
    setup_url = (
        f"{base}/investor-frontend/setup-password.html?token={raw_token}"
    )
    delivery = record_and_send(
        db,
        recipient=subscriber.email,
        subscriber_id=subscriber.id,
        message_type="ACCOUNT_SETUP",
        subject="Set up your Bethel subscriber account",
        text_body=(
            f"Hello {subscriber.name},\\n\\n"
            "Use this one-time link to create your subscriber password. "
            "It expires in 24 hours:\\n"
            f"{setup_url}\\n\\n"
            "If you were not expecting this invitation, ignore this message."
        ),
    )
    db.commit()

    return {
        "status": "success",
        "subscriber_id": subscriber_id,
        "setup_url": setup_url,
        "expires_at": expires_at.isoformat() + "Z",
        "message": "One-time setup link created; it expires in 24 hours",
        "email_status": delivery.status,
    }


@router.post("/copytrading/auth/setup-password")
def setup_subscriber_password(
    data: PasswordSetupRequest,
    db: Session = Depends(get_db),
):
    validate_password(data.password)
    now = datetime.utcnow()
    invite = (
        db.query(SubscriberInvite)
        .filter(
            SubscriberInvite.token_hash == token_digest(data.token),
            SubscriberInvite.used_at.is_(None),
        )
        .first()
    )
    if invite is None or invite.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup link is invalid, expired, or already used",
        )

    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == invite.subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    subscriber.password_hash = hash_password(data.password)
    invite.used_at = now
    db.commit()
    return {
        "status": "success",
        "subscriber_id": subscriber.id,
        "message": "Password created. You can now sign in.",
    }
