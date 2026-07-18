from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from api.database import Base



class MT5Account(Base):

    __tablename__ = "mt5_accounts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    account_number = Column(
        String,
        unique=True
    )

    server = Column(
        String
    )

    investor_password = Column(
        String
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



class AccountStatistics(Base):

    __tablename__ = "account_statistics"


    id = Column(
        Integer,
        primary_key=True
    )

    account_id = Column(
        Integer
    )

    balance = Column(
        Float
    )

    equity = Column(
        Float
    )

    profit = Column(
        Float
    )

    drawdown = Column(
        Float
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )



class Trade(Base):

    __tablename__ = "trades"


    id = Column(
        Integer,
        primary_key=True
    )


    account_id = Column(
        Integer
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



class Position(Base):

    __tablename__ = "positions"


    id = Column(
        Integer,
        primary_key=True
    )


    account_id = Column(
        Integer
    )


    ticket = Column(
        String
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
        Float
    )