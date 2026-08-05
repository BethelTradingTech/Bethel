from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint

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


class ConnectorPosition(Base):
    __tablename__ = "connector_positions"

    id = Column(Integer, primary_key=True)
    connector_id = Column(String(100), nullable=False, index=True)
    ticket = Column(String(40), nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    direction = Column(String(8), nullable=False)
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False, default=0)
    take_profit = Column(Float, nullable=False, default=0)
    profit = Column(Float, nullable=False, default=0)
    swap = Column(Float, nullable=False, default=0)
    opened_at = Column(DateTime, nullable=True)
    observed_at = Column(DateTime, nullable=False, index=True)


class ConnectorDeal(Base):
    __tablename__ = "connector_deals"
    __table_args__ = (UniqueConstraint("connector_id", "deal_ticket", name="uq_connector_deal_ticket"),)

    id = Column(Integer, primary_key=True)
    connector_id = Column(String(100), nullable=False, index=True)
    account_number = Column(String(32), nullable=False, index=True)
    deal_ticket = Column(String(40), nullable=False, index=True)
    position_id = Column(String(40), nullable=False, index=True)
    order_id = Column(String(40), nullable=False)
    symbol = Column(String(32), nullable=False, index=True)
    deal_type = Column(String(8), nullable=False)
    volume = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    profit = Column(Float, nullable=False, default=0)
    commission = Column(Float, nullable=False, default=0)
    swap = Column(Float, nullable=False, default=0)
    fee = Column(Float, nullable=False, default=0)
    closed_at = Column(DateTime, nullable=False, index=True)
    received_at = Column(DateTime, default=utc_now, nullable=False)


class ConnectorCashFlow(Base):
    __tablename__ = "connector_cash_flows"
    __table_args__ = (UniqueConstraint("connector_id", "deal_ticket", name="uq_connector_cash_flow_ticket"),)

    id = Column(Integer, primary_key=True)
    connector_id = Column(String(100), nullable=False, index=True)
    account_number = Column(String(32), nullable=False, index=True)
    deal_ticket = Column(String(40), nullable=False, index=True)
    event_type = Column(String(24), nullable=False)
    amount = Column(Float, nullable=False)
    occurred_at = Column(DateTime, nullable=False, index=True)
    received_at = Column(DateTime, default=utc_now, nullable=False)
