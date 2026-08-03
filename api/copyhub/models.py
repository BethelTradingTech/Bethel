from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint

from api.database import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CopyChannel(Base):
    __tablename__ = "copy_channels"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    master_account = Column(String(32), nullable=False, unique=True, index=True)
    active = Column(Boolean, nullable=False, default=True)
    globally_paused = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class CopyReceiver(Base):
    __tablename__ = "copy_receivers"
    __table_args__ = (UniqueConstraint("channel_id", "account_number", name="uq_copy_receiver_account"),)

    id = Column(Integer, primary_key=True)
    receiver_id = Column(String(80), nullable=False, unique=True, index=True)
    channel_id = Column(Integer, ForeignKey("copy_channels.id"), nullable=False, index=True)
    subscriber_id = Column(Integer, ForeignKey("copy_subscribers.id"), nullable=False, index=True)
    broker_account_id = Column(Integer, ForeignKey("broker_accounts.id"), nullable=False, unique=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    account_number = Column(String(32), nullable=False, index=True)
    platform = Column(String(32), nullable=False, default="MT5")
    environment = Column(String(8), nullable=False)  # DEMO or LIVE
    currency_unit = Column(String(8), nullable=False)  # USD or USC
    is_cent_account = Column(Boolean, nullable=False)
    contract_size = Column(Float, nullable=True)
    min_lot = Column(Float, nullable=True)
    max_lot = Column(Float, nullable=True)
    lot_step = Column(Float, nullable=True)
    sizing_mode = Column(String(32), nullable=False, default="SAME_AS_MASTER")
    lot_multiplier = Column(Float, nullable=False, default=1.0)
    metadata_verified = Column(Boolean, nullable=False, default=False)
    live_authorized = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=False)
    paused = Column(Boolean, nullable=False, default=True)
    last_heartbeat_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class CopyEvent(Base):
    __tablename__ = "copy_events"
    __table_args__ = (UniqueConstraint("channel_id", "event_key", name="uq_copy_event_key"),)

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("copy_channels.id"), nullable=False, index=True)
    event_key = Column(String(100), nullable=False)
    master_ticket = Column(String(40), nullable=False, index=True)
    event_type = Column(String(24), nullable=False, index=True)
    symbol = Column(String(32), nullable=False)
    direction = Column(String(8), nullable=False)
    volume = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    payload_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)


class CopyDelivery(Base):
    __tablename__ = "copy_deliveries"
    __table_args__ = (UniqueConstraint("receiver_id", "event_id", name="uq_copy_delivery_event"),)

    id = Column(Integer, primary_key=True)
    receiver_id = Column(Integer, ForeignKey("copy_receivers.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("copy_events.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    receiver_ticket = Column(String(40), nullable=True)
    broker_code = Column(String(40), nullable=True)
    message = Column(String(500), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    delivered_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
