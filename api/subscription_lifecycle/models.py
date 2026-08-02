from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from api.database import Base


class SubscriptionLifecycle(Base):
    __tablename__ = "subscription_lifecycle"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, unique=True, index=True)
    plan_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False, index=True)
    grace_until = Column(DateTime, nullable=False, index=True)
    last_payment_reference = Column(String(150), nullable=True)
    manual_suspended = Column(Boolean, nullable=False, default=False)
    suspended_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SubscriptionAudit(Base):
    __tablename__ = "subscription_audit"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    action = Column(String(30), nullable=False)
    previous_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=False)
    reference = Column(String(150), nullable=True)
    administrator = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PromoRedemption(Base):
    """Immutable audit record for a redeemed subscription promotion."""

    __tablename__ = "promo_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    code_hash = Column(String(64), nullable=False, unique=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    broker_login = Column(String(100), nullable=False, index=True)
    original_amount_usd = Column(Float, nullable=False)
    discount_amount_usd = Column(Float, nullable=False)
    final_amount_usd = Column(Float, nullable=False)
    payment_reference = Column(String(150), nullable=False, unique=True)
    redeemed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
