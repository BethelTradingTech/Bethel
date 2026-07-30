from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from api.database import Base


MONEY = Numeric(20, 8)
UNITS = Numeric(24, 10)


class ManagedFund(Base):
    __tablename__ = "managed_funds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(20), nullable=False, default="SANDBOX", index=True)
    valuation_frequency = Column(String(20), nullable=False, default="MONTHLY")
    distribution_frequency = Column(String(20), nullable=False, default="QUARTERLY")
    performance_fee_rate = Column(Numeric(8, 6), nullable=False, default=0.20)
    total_units = Column(UNITS, nullable=False, default=0)
    net_asset_value = Column(MONEY, nullable=False, default=0)
    nav_per_unit = Column(MONEY, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class FundInvestorAccount(Base):
    __tablename__ = "fund_investor_accounts"
    __table_args__ = (
        UniqueConstraint("fund_id", "subscriber_id", name="uq_fund_subscriber"),
    )

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("managed_funds.id"), nullable=False, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    units = Column(UNITS, nullable=False, default=0)
    contributed_capital = Column(MONEY, nullable=False, default=0)
    high_water_mark_nav = Column(MONEY, nullable=False, default=1)
    accrued_investor_profit = Column(MONEY, nullable=False, default=0)
    accrued_performance_fee = Column(MONEY, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class FundLedgerEntry(Base):
    __tablename__ = "fund_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("managed_funds.id"), nullable=False, index=True)
    investor_account_id = Column(
        Integer,
        ForeignKey("fund_investor_accounts.id"),
        nullable=True,
        index=True,
    )
    entry_type = Column(String(40), nullable=False, index=True)
    amount = Column(MONEY, nullable=False)
    units = Column(UNITS, nullable=True)
    nav_per_unit = Column(MONEY, nullable=True)
    reference = Column(String(150), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class FundValuation(Base):
    __tablename__ = "fund_valuations"
    __table_args__ = (
        UniqueConstraint("fund_id", "valuation_at", name="uq_fund_valuation_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("managed_funds.id"), nullable=False, index=True)
    valuation_at = Column(DateTime, nullable=False, index=True)
    gross_assets = Column(MONEY, nullable=False)
    liabilities = Column(MONEY, nullable=False, default=0)
    net_asset_value = Column(MONEY, nullable=False)
    total_units = Column(UNITS, nullable=False)
    nav_per_unit = Column(MONEY, nullable=False)
    source = Column(String(40), nullable=False, default="SIMULATED")
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ProfitSharePeriod(Base):
    __tablename__ = "fund_profit_share_periods"
    __table_args__ = (
        UniqueConstraint(
            "fund_id",
            "period_start",
            "period_end",
            name="uq_fund_profit_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("managed_funds.id"), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    closing_nav_per_unit = Column(MONEY, nullable=False)
    gross_eligible_profit = Column(MONEY, nullable=False, default=0)
    investor_profit = Column(MONEY, nullable=False, default=0)
    performance_fee = Column(MONEY, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="SANDBOX_CALCULATED")
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class InvestorProfitAllocation(Base):
    __tablename__ = "fund_investor_profit_allocations"
    __table_args__ = (
        UniqueConstraint(
            "period_id",
            "investor_account_id",
            name="uq_period_investor_allocation",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(
        Integer,
        ForeignKey("fund_profit_share_periods.id"),
        nullable=False,
        index=True,
    )
    investor_account_id = Column(
        Integer,
        ForeignKey("fund_investor_accounts.id"),
        nullable=False,
        index=True,
    )
    opening_high_water_mark_nav = Column(MONEY, nullable=False)
    closing_nav_per_unit = Column(MONEY, nullable=False)
    units = Column(UNITS, nullable=False)
    gross_eligible_profit = Column(MONEY, nullable=False)
    performance_fee = Column(MONEY, nullable=False)
    investor_profit = Column(MONEY, nullable=False)
    status = Column(String(30), nullable=False, default="ACCRUED_SANDBOX")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class FundRedemptionRequest(Base):
    __tablename__ = "fund_redemption_requests"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("managed_funds.id"), nullable=False, index=True)
    investor_account_id = Column(
        Integer,
        ForeignKey("fund_investor_accounts.id"),
        nullable=False,
        index=True,
    )
    requested_units = Column(UNITS, nullable=False)
    estimated_nav_per_unit = Column(MONEY, nullable=False)
    estimated_amount = Column(MONEY, nullable=False)
    status = Column(String(30), nullable=False, default="PENDING_SANDBOX", index=True)
    reason = Column(String(500), nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
