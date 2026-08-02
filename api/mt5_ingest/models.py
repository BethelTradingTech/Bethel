from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from api.database import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConnectorNonce(Base):
    __tablename__ = "connector_nonces"

    id = Column(Integer, primary_key=True)
    connector_id = Column(String(100), nullable=False, index=True)
    nonce = Column(String(100), nullable=False, unique=True, index=True)
    received_at = Column(DateTime, default=utc_now, nullable=False, index=True)


class ConnectorStatus(Base):
    __tablename__ = "connector_status"

    id = Column(Integer, primary_key=True)
    connector_id = Column(String(100), nullable=False, unique=True, index=True)
    account_number = Column(String(32), nullable=False, index=True)
    server = Column(String(120), nullable=False)
    currency = Column(String(12), nullable=False)
    mode = Column(String(8), nullable=False)
    balance = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    floating_profit = Column(Float, nullable=False, default=0)
    observed_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, default=utc_now, nullable=False, index=True)
