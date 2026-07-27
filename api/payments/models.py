from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from api.database import Base


class BinancePayment(Base):
    __tablename__ = "binance_payments"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, nullable=False)
    merchant_trade_no = Column(String(32), unique=True, nullable=False, index=True)
    prepay_id = Column(String(64), nullable=True, index=True)
    fiat_amount = Column(Float, nullable=False)
    fiat_currency = Column(String(8), nullable=False, default="USD")
    payment_currency = Column(String(8), nullable=False, default="USDT")
    status = Column(String(24), nullable=False, default="INITIAL")
    checkout_url = Column(String(600), nullable=True)
    transaction_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
