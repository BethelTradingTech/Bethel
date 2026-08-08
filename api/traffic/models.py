from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from api.database import Base


class WebsiteTrafficEvent(Base):
    __tablename__ = "website_traffic_events"

    id = Column(Integer, primary_key=True)
    visitor_hash = Column(String(64), nullable=False, index=True)
    path = Column(String(255), nullable=False, index=True)
    referrer = Column(String(500), nullable=True)
    country = Column(String(8), nullable=True, index=True)
    region = Column(String(120), nullable=True)
    city = Column(String(120), nullable=True, index=True)
    browser = Column(String(40), nullable=True, index=True)
    device = Column(String(40), nullable=True, index=True)
    is_bot = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
