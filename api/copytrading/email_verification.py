from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from api.database import Base


class SubscriberEmailVerification(Base):
    """One active email-verification record per subscriber."""

    __tablename__ = "subscriber_email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, unique=True, index=True, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
