"""
Bethel Trading Technologies

Broker Account Linking Models

Purpose:
    Stores subscriber MT5 account connections.

Mode:
    Copy Trading Infrastructure
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from api.database import Base


class BrokerAccount(Base):

    __tablename__ = "broker_accounts"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    subscriber_id = Column(
        Integer,
        ForeignKey("copy_subscribers.id"),
        nullable=False
    )


    broker = Column(
        String,
        default="MT5"
    )


    login = Column(
        String,
        unique=True,
        nullable=False
    )


    server = Column(
        String,
        nullable=False
    )


    status = Column(
        String,
        default="PENDING"
    )


    currency = Column(
        String,
        default="USD"
    )


    leverage = Column(
        Integer,
        default=100
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )