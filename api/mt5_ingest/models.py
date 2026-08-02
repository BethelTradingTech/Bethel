from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from api.database import Base


class ConnectorNonce(Base):
    __tablename__ = "connector_nonces"

    id = Column(Integer, primary_key=True)
    connector_id = Column(String(100), nullable=False, index=True)
    nonce = Column(String(100), nullable=False, unique=True, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
