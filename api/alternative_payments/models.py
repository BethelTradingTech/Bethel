from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from api.database import Base


class PayPalPayment(Base):
    __tablename__ = "paypal_payments"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, nullable=False)
    order_id = Column(String(255), nullable=False, unique=True, index=True)
    capture_id = Column(String(255), nullable=True, unique=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(String(30), nullable=False, default="CREATED")
    approval_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class WisePayment(Base):
    __tablename__ = "wise_payments"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, nullable=False)
    reference = Column(String(150), nullable=False, unique=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(String(30), nullable=False, default="PENDING_VERIFICATION")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
