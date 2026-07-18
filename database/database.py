"""
Bethel Trading Technologies
Database Engine
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DATABASE_NAME = "bethel_trading.db"


DATABASE_URL = f"sqlite:///{DATABASE_NAME}"


engine = create_engine(
    DATABASE_URL,
    echo=False
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_database():

    database = SessionLocal()

    try:
        return database

    finally:
        database.close()


def database_status():

    return "Database Engine Online"