from datetime import datetime
from email.message import EmailMessage
import os
import smtplib
import ssl
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy.orm import Session

from api.notifications.models import EmailDelivery


# Subscriber authentication pages are served by the Bethel API application
# under /investor-frontend. Use the working Render origin for customer-facing
# reset/verification links until the custom api.betheltradingtechnologies.com
# hostname is healthy and explicitly verified.
PUBLIC_SUBSCRIBER_PORTAL = "https://bethel-api.onrender.com/investor-frontend"


def _smtp_from_address() -> str:
    """Return the configured SMTP sender, supporting the legacy/new env names."""
    return (os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_FROM") or "").strip()


def smtp_configured() -> bool:
    required = ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD")
    return all(os.getenv(name) for name in required) and bool(_smtp_from_address())


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
        delivery.status = "SMTP_NOT_CONFIGURED"
        delivery.error = "SMTP environment variables are not configured"
        return delivery

    message = EmailMessage()
    message["From"] = _smtp_from_address()
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


def _subscriber_portal_base() -> str:
    raw = os.getenv("SUBSCRIBER_PORTAL_URL", PUBLIC_SUBSCRIBER_PORTAL).strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    elif raw and not raw.startswith(("http://", "https://")):
        raw = "https://" + raw.lstrip("/")

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return PUBLIC_SUBSCRIBER_PORTAL

    # The reset page uses relative API routes and therefore must live on the
    # same application origin that serves the subscriber backend. Normalize
    # known non-working or marketing hosts to the verified Render portal.
    hostname = (parsed.hostname or "").lower()
    if hostname in {
        "api.betheltradingtechnologies.com",
        "betheltradingtechnologies.com",
        "www.betheltradingtechnologies.com",
    }:
        return PUBLIC_SUBSCRIBER_PORTAL

    return raw.rstrip("/")


def portal_url(path: str) -> str:
    return f"{_subscriber_portal_base()}/{path.lstrip('/')}"
