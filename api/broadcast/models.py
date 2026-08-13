from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from api.database import Base

def utc_now(): return datetime.now(timezone.utc).replace(tzinfo=None)

class BroadcastControl(Base):
    __tablename__ = "broadcast_control"
    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, nullable=False, default=False)
    terminal_registry_id = Column(Integer, nullable=True, index=True)
    landscape_enabled = Column(Boolean, nullable=False, default=True)
    vertical_enabled = Column(Boolean, nullable=False, default=True)
    website_enabled = Column(Boolean, nullable=False, default=False)
    youtube_enabled = Column(Boolean, nullable=False, default=False)
    facebook_enabled = Column(Boolean, nullable=False, default=False)
    instagram_enabled = Column(Boolean, nullable=False, default=False)
    tiktok_enabled = Column(Boolean, nullable=False, default=False)
    worker_state = Column(String(32), nullable=False, default="OFF")
    worker_message = Column(String(255), nullable=True)
    worker_last_seen = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now, nullable=False, onupdate=utc_now)
