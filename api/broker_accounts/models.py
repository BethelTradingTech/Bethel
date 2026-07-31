"""Broker-account records for Bethel's non-custodial copy-trading system."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from api.database import Base


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(
        Integer,
        ForeignKey("copy_subscribers.id"),
        nullable=False,
        index=True,
    )

    # broker is the financial institution; platform is its trading technology.
    broker = Column(String(100), nullable=False)
    platform = Column(String(32), nullable=False, default="MT5", index=True)
    login = Column(String(100), unique=True, nullable=False)
    server = Column(String(255), nullable=False)

    status = Column(String(32), default="PENDING_AUTHORIZATION", index=True)
    connection_method = Column(String(32), default="LOCAL_TERMINAL")
    execution_mode = Column(String(16), nullable=False, default="PAPER")
    live_authorized = Column(Boolean, nullable=False, default=False, index=True)
    live_authorized_at = Column(DateTime, nullable=True)
    live_authorized_by = Column(String(255), nullable=True)

    currency = Column(String(12), default="USD")
    leverage = Column(Integer, default=100)
    last_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
