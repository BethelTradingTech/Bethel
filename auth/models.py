"""
Bethel Trading Technologies
User Authentication Database Models
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime
)

from datetime import datetime

from api.database import Base



class User(Base):

    __tablename__ = "users"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    # Login email

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )


    # Encrypted password

    hashed_password = Column(
        String,
        nullable=False
    )


    # User profile

    full_name = Column(
        String,
        nullable=True
    )


    country = Column(
        String,
        nullable=True
    )


    phone = Column(
        String,
        nullable=True
    )


    # Account status

    is_active = Column(
        Boolean,
        default=True
    )


    # KYC preparation
    # Future Sumsub integration

    kyc_status = Column(
        String,
        default="PENDING"
    )


    # Subscription / copy trading

    account_type = Column(
        String,
        default="CLIENT"
    )


    subscription_status = Column(
        String,
        default="FREE"
    )


    # Dates

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )