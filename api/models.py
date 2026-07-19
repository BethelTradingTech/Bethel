"""
Bethel Trading Technologies
Database Models
"""

from sqlalchemy import Column, Integer, String, Float, DateTime

from datetime import datetime

from api.database import Base



# ==========================
# MT5 ACCOUNT
# ==========================

class MT5Account(Base):

    __tablename__ = "mt5_accounts"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    account_number = Column(
        String,
        unique=True,
        index=True
    )


    server = Column(
        String
    )


    investor_password = Column(
        String,
        nullable=True
    )


    broker = Column(
        String,
        nullable=True
    )


    status = Column(
        String,
        default="DISCONNECTED"
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )





# ==========================
# ACCOUNT STATISTICS
# ==========================

class AccountStatistics(Base):

    __tablename__ = "account_statistics"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    account_id = Column(
        Integer,
        index=True
    )


    balance = Column(
        Float,
        default=0
    )


    equity = Column(
        Float,
        default=0
    )


    profit = Column(
        Float,
        default=0
    )


    drawdown = Column(
        Float,
        default=0
    )


    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )





# ==========================
# EQUITY HISTORY / INVESTOR PERFORMANCE
# ==========================

class EquitySnapshot(Base):

    __tablename__ = "equity_snapshots"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    account_id = Column(
        Integer,
        index=True
    )


    account_number = Column(
        String,
        index=True
    )



    # ACCOUNT VALUES

    balance = Column(
        Float,
        nullable=False
    )


    equity = Column(
        Float,
        nullable=False
    )


    profit = Column(
        Float,
        default=0
    )


    drawdown = Column(
        Float,
        default=0
    )



    # PERFORMANCE METRICS


    peak_equity = Column(
        Float,
        default=0
    )


    daily_return = Column(
        Float,
        default=0
    )


    monthly_return = Column(
        Float,
        default=0
    )


    total_return = Column(
        Float,
        default=0
    )



    # RISK METRICS


    volatility = Column(
        Float,
        default=0
    )


    sharpe_ratio = Column(
        Float,
        default=0
    )



    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )





# ==========================
# TRADE HISTORY
# ==========================

class Trade(Base):

    __tablename__ = "trades"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    account_id = Column(
        Integer,
        index=True
    )


    ticket = Column(
        String,
        nullable=True
    )


    symbol = Column(
        String
    )


    direction = Column(
        String
    )


    lot_size = Column(
        Float
    )


    entry_price = Column(
        Float
    )


    exit_price = Column(
        Float,
        nullable=True
    )


    profit = Column(
        Float,
        default=0
    )


    status = Column(
        String,
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





# ==========================
# OPEN POSITIONS
# ==========================

class Position(Base):

    __tablename__ = "positions"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    account_id = Column(
        Integer,
        index=True
    )


    ticket = Column(
        String,
        index=True
    )


    symbol = Column(
        String
    )


    type = Column(
        String
    )


    volume = Column(
        Float
    )


    open_price = Column(
        Float
    )


    current_price = Column(
        Float
    )


    profit = Column(
        Float,
        default=0
    )


    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )