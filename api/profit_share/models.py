from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint

from api.database import Base


class ProfitShareAgreement(Base):
    __tablename__ = "profit_share_agreements"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, unique=True, index=True)
    version = Column(String(30), nullable=False)
    fee_rate = Column(Float, nullable=False, default=0.20)
    accepted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(String(80), nullable=True)
    user_agent = Column(String(500), nullable=True)
    revoked_at = Column(DateTime, nullable=True)


class ProfitShareAccount(Base):
    __tablename__ = "profit_share_accounts"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, unique=True, index=True)
    fee_rate = Column(Float, nullable=False, default=0.20)
    currency = Column(String(10), nullable=False, default="USD")
    fee_start_at = Column(DateTime, nullable=False)
    baseline_cumulative_profit = Column(Float, nullable=False, default=0.0)
    high_water_mark = Column(Float, nullable=False, default=0.0)
    last_crystallized_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ProfitShareStatement(Base):
    __tablename__ = "profit_share_statements"
    __table_args__ = (
        UniqueConstraint(
            "subscriber_id",
            "period_start",
            "period_end",
            name="uq_profit_share_statement_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    cumulative_net_profit = Column(Float, nullable=False)
    previous_high_water_mark = Column(Float, nullable=False)
    eligible_profit = Column(Float, nullable=False)
    fee_rate = Column(Float, nullable=False)
    fee_due = Column(Float, nullable=False)
    subscriber_profit_share = Column(Float, nullable=False)
    new_high_water_mark = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="DRAFT", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finalized_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)


class ProfitShareAudit(Base):
    __tablename__ = "profit_share_audit"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    statement_id = Column(Integer, nullable=True, index=True)
    action = Column(String(30), nullable=False)
    administrator = Column(String(255), nullable=True)
    details = Column(String(1000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
