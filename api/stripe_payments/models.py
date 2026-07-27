from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from api.database import Base


class StripePayment(Base):
    __tablename__ = "stripe_payments"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, nullable=False)
    checkout_session_id = Column(String(255), nullable=False, unique=True, index=True)
    payment_intent_id = Column(String(255), nullable=True, unique=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    status = Column(String(30), nullable=False, default="PENDING")
    checkout_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
