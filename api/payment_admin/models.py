from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from api.database import Base


class PaymentAudit(Base):
    __tablename__ = "payment_audit"

    id = Column(Integer, primary_key=True, index=True)
    method = Column(String(20), nullable=False, index=True)
    payment_id = Column(String(100), nullable=False, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    action = Column(String(30), nullable=False)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    administrator = Column(String(255), nullable=True)
    reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
