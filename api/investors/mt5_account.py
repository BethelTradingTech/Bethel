"""
Bethel Trading Technologies
Investor MT5 Account Model
"""


from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime
)

from datetime import datetime

from api.database import Base



class MT5Account(Base):

    __tablename__ = "mt5_accounts"


    id = Column(

        Integer,

        primary_key=True,

        index=True

    )


    investor_id = Column(

        Integer,

        nullable=False

    )


    portfolio_id = Column(

        Integer,

        nullable=False

    )


    mt5_login = Column(

        String,

        nullable=False

    )


    broker = Column(

        String

    )


    server = Column(

        String

    )


    currency = Column(

        String,

        default="USD"

    )


    initial_balance = Column(

        Float,

        default=0

    )


    current_balance = Column(

        Float,

        default=0

    )


    current_equity = Column(

        Float,

        default=0

    )


    status = Column(

        String,

        default="active"

    )


    created_at = Column(

        DateTime,

        default=datetime.utcnow

    )