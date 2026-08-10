"""Canonical SQLAlchemy models for subscriber authentication security records.

Render/Gunicorn can load compatibility modules through more than one Python
import path during startup. Keep the model canonical here and allow SQLAlchemy
to reuse the already-registered Table object if this module is evaluated again.
This does not create, drop, or alter the database table.
"""

from datetime import datetime
import sys

from sqlalchemy import Column, DateTime, Integer, String

from api.database import Base


class SubscriberPasswordReset(Base):
    """One active password-reset record per subscriber."""

    __tablename__ = "subscriber_password_resets"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, unique=True, index=True, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Render can expose this package through more than one import root. Register
# both module names to this single module object so SQLAlchemy does not evaluate
# the same declarative model twice under alternate import names.
_this_module = sys.modules[__name__]
sys.modules.setdefault("api.copytrading.subscriber_security_models", _this_module)
sys.modules.setdefault("copytrading.subscriber_security_models", _this_module)
