from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from api.database import Base


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


class PasswordReset(Base):
    __tablename__ = "subscriber_password_resets"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(
        Integer,
        ForeignKey("copy_subscribers.id"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


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
