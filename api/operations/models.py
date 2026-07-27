from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from api.database import Base


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, unique=True, index=True)
    sha256 = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    reason = Column(String(50), nullable=False)
    integrity_status = Column(String(30), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    method = Column(String(10), nullable=True)
    path = Column(String(500), nullable=True, index=True)
    status_code = Column(Integer, nullable=True, index=True)
    actor = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(80), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
