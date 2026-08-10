"""Canonical SQLAlchemy models for subscriber authentication security records.

Keep these declarations in one import path so Render/Gunicorn startup cannot
register the same table twice when compatibility modules are imported.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from api.database import Base


class SubscriberPasswordReset(Base):
    """One active password-reset record per subscriber."""

    __tablename__ = "subscriber_password_resets"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, unique=True, index=True, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
