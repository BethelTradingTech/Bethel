from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from api.database import Base


class SubscriberInvite(Base):
    __tablename__ = "subscriber_invites"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(
        Integer,
        ForeignKey("copy_subscribers.id"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
