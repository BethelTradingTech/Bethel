from sqlalchemy import Column,Integer,String,ForeignKey
from api.database import Base


class InvestorUser(Base):

    __tablename__ = "investor_users"


    id = Column(
        Integer,
        primary_key=True
    )


    investor_id = Column(
        Integer,
        ForeignKey("investors.id")
    )


    email = Column(
        String,
        unique=True,
        nullable=False
    )


    password_hash = Column(
        String,
        nullable=False
    )


    role = Column(
        String,
        default="investor"
    )