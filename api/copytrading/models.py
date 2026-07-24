from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean
)
from api.database import Base


# ==========================
# MASTER TRADES
# ==========================

class MasterTrade(Base):
    __tablename__ = "master_trades"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    ticket = Column(
        Integer,
        unique=True,
        index=True,
        nullable=False
    )
    symbol = Column(
        String(20),
        nullable=False
    )
    direction = Column(
        String(10),
        nullable=False
    )
    volume = Column(
        Float,
        nullable=False
    )
    entry_price = Column(
        Float,
        nullable=False
    )
    stop_loss = Column(
        Float,
        nullable=True
    )
    take_profit = Column(
        Float,
        nullable=True
    )
    current_price = Column(
        Float,
        nullable=True
    )
    profit = Column(
        Float,
        default=0.0
    )
    status = Column(
        String(20),
        default="OPEN"
    )
    magic_number = Column(
        Integer,
        nullable=True
    )
    comment = Column(
        String(100),
        nullable=True
    )
    opened_at = Column(
        DateTime,
        nullable=True
    )
    closed_at = Column(
        DateTime,
        nullable=True
    )
    last_seen = Column(
        DateTime,
        nullable=True
    )
    synchronized = Column(
        Boolean,
        default=False
    )


# ==========================
# COPY SUBSCRIBERS
# ==========================

class CopySubscriber(Base):
    __tablename__ = "copy_subscribers"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    investor_id = Column(
        Integer,
        index=True,
        nullable=True
    )
    name = Column(
        String(100),
        nullable=False
    )
    email = Column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )
    password_hash = Column(
        String(255),
        nullable=True
    )
    broker = Column(
        String(100),
        nullable=True
    )
    mt5_account = Column(
        String(50),
        unique=True,
        nullable=False
    )
    mt5_account_id = Column(
        Integer,
        nullable=True
    )
    risk_multiplier = Column(
        Float,
        default=1.0
    )
    allocation_percent = Column(
        Float,
        default=100.0
    )
    status = Column(
        String(20),
        default="PENDING"
    )
    payment_status = Column(
        String(20),
        default="UNPAID"
    )
    activated_at = Column(
        DateTime,
        nullable=True
    )
    synchronized = Column(
        Boolean,
        default=False
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================
# COPY ORDERS
# ==========================

class CopyOrder(Base):
    __tablename__ = "copy_orders"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    subscriber_id = Column(
        Integer,
        index=True,
        nullable=False
    )
    subscriber_account = Column(
        String(50),
        nullable=False
    )
    master_ticket = Column(
        Integer,
        index=True,
        nullable=False
    )
    symbol = Column(
        String(20),
        nullable=False
    )
    direction = Column(
        String(10),
        nullable=False
    )
    volume = Column(
        Float,
        nullable=False
    )
    entry_price = Column(
        Float,
        nullable=False
    )
    stop_loss = Column(
        Float,
        nullable=True
    )
    take_profit = Column(
        Float,
        nullable=True
    )
    status = Column(
        String(20),
        default="PAPER"
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    executed_at = Column(
        DateTime,
        nullable=True
    )


# ==========================
# TRADE SYNC QUEUE
# ==========================

class TradeSyncQueue(Base):
    __tablename__ = "trade_sync_queue"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    master_ticket = Column(
        Integer,
        index=True,
        nullable=False
    )
    subscriber_id = Column(
        Integer,
        index=True,
        nullable=False
    )
    action = Column(
        String(30),
        nullable=False
    )
    old_value = Column(
        String(100),
        nullable=True
    )
    new_value = Column(
        String(100),
        nullable=True
    )
    status = Column(
        String(20),
        default="PENDING"
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    processed_at = Column(
        DateTime,
        nullable=True
    )


# ==========================
# COPY EXECUTION LOGS
# ==========================

class CopyExecutionLog(Base):
    __tablename__ = "copy_execution_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    investor_id = Column(
        Integer,
        index=True,
        nullable=True
    )
    copy_order_id = Column(
        Integer,
        index=True,
        nullable=False
    )
    subscriber_id = Column(
        Integer,
        index=True,
        nullable=False
    )
    symbol = Column(
        String(20),
        nullable=False
    )
    direction = Column(
        String(10),
        nullable=False
    )
    requested_volume = Column(
        Float,
        nullable=False
    )
    executed_volume = Column(
        Float,
        nullable=False
    )
    mode = Column(
        String(20),
        default="PAPER"
    )
    status = Column(
        String(20),
        default="SUCCESS"
    )
    error_message = Column(
        String(255),
        nullable=True
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

   # ==========================
# COPY TRADE PERFORMANCE
# ==========================

class CopyTradePerformance(Base):
    __tablename__ = "copy_trade_performance"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    subscriber_id = Column(
        Integer,
        index=True,
        nullable=False
    )

    copy_order_id = Column(
        Integer,
        index=True,
        nullable=False
    )

    symbol = Column(
        String(20),
        nullable=False
    )

    direction = Column(
        String(10),
        nullable=False
    )

    entry_price = Column(
        Float,
        nullable=False
    )

    exit_price = Column(
        Float,
        nullable=True
    )

    volume = Column(
        Float,
        nullable=False
    )

    profit_loss = Column(
        Float,
        default=0.0
    )

    profit_percent = Column(
        Float,
        default=0.0
    )

    status = Column(
        String(20),
        default="OPEN"
    )

    opened_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    closed_at = Column(
        DateTime,
        nullable=True
    )