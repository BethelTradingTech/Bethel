"""Canonical SQLAlchemy models for subscriber authentication security records.

Render/Gunicorn can expose the same source file through more than one Python
import root. Register every supported import alias before SQLAlchemy evaluates
the declarative class so the password-reset table is mapped only once.
This does not create, drop, or alter an existing database table.
"""

from datetime import datetime
import sys

from sqlalchemy import Column, DateTime, Integer, String

from api.database import Base


# IMPORTANT: register aliases before the declarative class is evaluated.
# This prevents a second execution of this module when Render resolves the
# package as api.copytrading.*, copytrading.*, or a bare compatibility import.
_this_module = sys.modules[__name__]
for _alias in (
    "api.copytrading.subscriber_security_models",
    "copytrading.subscriber_security_models",
    "subscriber_security_models",
):
    sys.modules.setdefault(_alias, _this_module)


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
