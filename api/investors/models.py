"""
Bethel Trading Technologies
Investor & Portfolio Database Models
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



# ======================================
# INVESTOR PROFILE
# ======================================


class Investor(Base):

    __tablename__ = "investors"


    id = Column(

        Integer,

        primary_key=True,

        index=True

    )


    name = Column(

        String,

        nullable=False

    )


    email = Column(

        String,

        unique=True,

        index=True,

        nullable=False

    )


    phone = Column(

        String

    )


    country = Column(

        String

    )


    capital = Column(

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





# ======================================
# INVESTOR PORTFOLIO
# ======================================


class Portfolio(Base):

    __tablename__ = "portfolios"



    id = Column(

        Integer,

        primary_key=True,

        index=True

    )



    investor_id = Column(

        Integer,

        nullable=False

    )



    portfolio_name = Column(

        String,

        default="Bethel Growth Portfolio"

    )



    starting_capital = Column(

        Float,

        default=0

    )



    current_value = Column(

        Float,

        default=0

    )



    total_return = Column(

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