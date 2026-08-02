from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from api.database import Base


class SuperAdminProfile(Base):
    """Owner identity details kept separate from general user accounts."""

    __tablename__ = "super_admin_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    mobile_number = Column(String(16), nullable=False, unique=True, index=True)
    mobile_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
