from datetime import datetime
from email.message import EmailMessage
import os
import smtplib
import ssl
from uuid import uuid4

from sqlalchemy.orm import Session

from api.notifications.models import EmailDelivery


def smtp_configured() -> bool:
    return all(
        os.getenv(name)
        for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL")
    )


def record_and_send(
    db: Session,
    *,
    recipient: str,
    message_type: str,
    subject: str,
    text_body: str,
    subscriber_id: int | None = None,
    deduplication_key: str | None = None,
) -> EmailDelivery:
    if deduplication_key:
        existing = (
            db.query(EmailDelivery)
            .filter(EmailDelivery.deduplication_key == deduplication_key)
            .first()
        )
        if existing:
            return existing

    delivery = EmailDelivery(
        subscriber_id=subscriber_id,
        recipient=recipient,
        message_type=message_type,
        subject=subject,
        status="PENDING",
        deduplication_key=deduplication_key,
    )
    db.add(delivery)
    db.flush()
    delivery.attempts += 1

    if not smtp_configured():
        delivery.status = "CONFIGURATION_REQUIRED"
        delivery.error = "SMTP environment variables are not configured"
        return delivery

    message = EmailMessage()
    message["From"] = os.environ["SMTP_FROM_EMAIL"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")
    use_starttls = os.getenv("SMTP_USE_STARTTLS", "true").lower() in ("1", "true", "yes")

    try:
        if use_ssl:
            connection = smtplib.SMTP_SSL(
                host,
                port,
                timeout=20,
                context=ssl.create_default_context(),
            )
        else:
            connection = smtplib.SMTP(host, port, timeout=20)
        with connection:
            connection.ehlo()
            if not use_ssl and use_starttls:
                connection.starttls(context=ssl.create_default_context())
                connection.ehlo()
            connection.login(username, password)
            connection.send_message(message)
        delivery.status = "SENT"
        delivery.sent_at = datetime.utcnow()
        delivery.provider_message_id = f"smtp-{uuid4().hex}"
        delivery.error = None
    except Exception as error:
        delivery.status = "FAILED"
        delivery.error = str(error)[:2000]
    return delivery


def portal_url(path: str) -> str:
    base = os.getenv(
        "SUBSCRIBER_PORTAL_URL",
        "http://127.0.0.1:8000/investor-frontend",
    ).rstrip("/")
    return f"{base}/{path.lstrip('/')}"
