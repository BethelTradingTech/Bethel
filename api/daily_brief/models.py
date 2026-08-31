from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, Text

from api.database import Base


class DailyMarketBrief(Base):
    __tablename__ = "daily_market_briefs"

    id = Column(Integer, primary_key=True)
    brief_date = Column(Date, nullable=False, unique=True, index=True)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    body = Column(Text, nullable=False)
    social_text = Column(Text, nullable=False)
    source_health = Column(Text, nullable=True)
    social_status = Column(Text, nullable=True)
