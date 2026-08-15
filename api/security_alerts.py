"""Best-effort, rate-limited email alerts for Bethel security events.

Security enforcement must never depend on email delivery. These helpers record
and attempt alerts through the existing SMTP notification subsystem while
suppressing duplicates within a configurable time bucket.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os

from api.database import SessionLocal
from api.notifications.emailer import record_and_send


def _recipient() -> str | None:
    value = (os.getenv("SECURITY_ALERT_EMAIL") or os.getenv("SMTP_FROM_EMAIL") or "").strip()
    return value or None


def send_security_alert(*, event: str, severity: str, summary: str, details: str = "") -> bool:
    recipient = _recipient()
    if not recipient:
        return False

    try:
        bucket_minutes = max(5, min(int(os.getenv("SECURITY_ALERT_DEDUP_MINUTES", "30")), 1440))
    except ValueError:
        bucket_minutes = 30

    now = datetime.now(timezone.utc)
    bucket = int(now.timestamp() // (bucket_minutes * 60))
    event_key = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in event.lower())[:80]
    deduplication_key = f"security-alert:{event_key}:{bucket}"

    text = (
        f"BETHEL SECURITY ALERT — {severity.upper()}\n\n"
        f"Event: {event}\n"
        f"Time (UTC): {now.isoformat()}\n"
        f"Summary: {summary}\n"
    )
    if details:
        text += f"Details: {details[:3000]}\n"
    text += "\nThis is an automated security notification. Review the production logs and affected control before taking action."

    db = SessionLocal()
    try:
        delivery = record_and_send(
            db,
            recipient=recipient,
            message_type="SECURITY_ALERT",
            subject=f"[Bethel Security] {severity.upper()}: {event}",
            text_body=text,
            deduplication_key=deduplication_key,
        )
        db.commit()
        return delivery.status == "SENT"
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()
