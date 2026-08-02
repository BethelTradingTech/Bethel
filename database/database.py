"""
Bethel Trading Technologies
Database Engine
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


DATABASE_NAME = "bethel_trading.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_NAME}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)


engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


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
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "Database Engine Online"
    except Exception:
        return "Database Engine Unavailable"
