from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, UniqueConstraint

from api.database import Base


class PaymentAudit(Base):
    __tablename__ = "payment_audit"

    id = Column(Integer, primary_key=True, index=True)
    method = Column(String(20), nullable=False, index=True)
    payment_id = Column(String(100), nullable=False, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    action = Column(String(30), nullable=False)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    administrator = Column(String(255), nullable=True)
    reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(40), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    discount_type = Column(String(20), nullable=False, default="FIXED")
    discount_value = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    restricted_email = Column(String(255), nullable=True, index=True)
    max_uses = Column(Integer, nullable=True)
    uses_count = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True, index=True)
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"
    __table_args__ = (
        UniqueConstraint("promo_code_id", "subscriber_id", name="uq_promo_subscriber_once"),
    )

    id = Column(Integer, primary_key=True, index=True)
    promo_code_id = Column(Integer, nullable=False, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, nullable=False)
    original_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, nullable=False)
    final_amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(20), nullable=False, default="APPLIED")
    redeemed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
