from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from api.database import Base
from api.copytrading.subscriber_security_models import SubscriberPasswordReset as PasswordReset


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=True, index=True)
    recipient = Column(String(255), nullable=False, index=True)
    message_type = Column(String(50), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    provider_message_id = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    deduplication_key = Column(String(255), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)


class NotificationState(Base):
    __tablename__ = "subscriber_notification_state"
    __table_args__ = (
        UniqueConstraint("subscriber_id", name="uq_subscriber_notification_state"),
    )

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    kyc_status = Column(String(30), nullable=True)
    payment_status = Column(String(30), nullable=True)
    activation_status = Column(String(30), nullable=True)
    subscription_status = Column(String(30), nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
