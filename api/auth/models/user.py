from sqlalchemy import Column, Integer, String, Boolean
from api.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    email = Column(
        String,
        unique=True,
        index=True
    )

    password_hash = Column(
        String
    )

    role = Column(
        String,
        default="investor"
    )

    active = Column(
        Boolean,
        default=True
    )