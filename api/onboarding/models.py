from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from api.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    billing_interval = Column(String(20), nullable=False, default="MONTHLY")
    allocation_percent = Column(Float, nullable=False, default=100.0)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ClientOnboarding(Base):
    __tablename__ = "client_onboarding"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, unique=True, index=True, nullable=False)
    plan_id = Column(Integer, nullable=True)
    subscription_status = Column(String(20), nullable=False, default="NOT_SELECTED")
    kyc_status = Column(String(20), nullable=False, default="NOT_STARTED")
    payment_status = Column(String(20), nullable=False, default="UNPAID")
    payment_reference = Column(String(150), nullable=True)
    broker_status = Column(String(20), nullable=False, default="NOT_CONNECTED")
    admin_approval = Column(String(20), nullable=False, default="PENDING")
    copy_trading_status = Column(String(20), nullable=False, default="INACTIVE")
    rejection_reason = Column(String(500), nullable=True)
    kyc_submitted_at = Column(DateTime, nullable=True)
    kyc_reviewed_at = Column(DateTime, nullable=True)
    payment_confirmed_at = Column(DateTime, nullable=True)
    activation_fee_satisfied_at = Column(DateTime, nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
