from datetime import datetime
from sqlalchemy.orm import Session

from api.fund_management.accounting import (
    ONE,
    ZERO,
    calculate_nav,
    calculate_profit_share,
    calculate_subscription_units,
    decimal_value,
    money,
    units,
)
from api.fund_management.config import assert_safe_configuration
from api.fund_management.models import (
    FundInvestorAccount,
    FundLedgerEntry,
    FundRedemptionRequest,
    FundValuation,
    InvestorProfitAllocation,
    ManagedFund,
    ProfitSharePeriod,
)


def create_fund(
    db: Session,
    *,
    name: str,
    currency: str,
    performance_fee_rate,
) -> ManagedFund:
    controls = assert_safe_configuration()
    if not controls["platform_enabled"]:
        raise RuntimeError("Fund platform is disabled")
    rate = decimal_value(performance_fee_rate)
    if rate < ZERO or rate > ONE:
        raise ValueError("Performance fee rate must be between 0 and 1")
    fund = ManagedFund(
        name=name.strip(),
        currency=currency.upper(),
        performance_fee_rate=rate,
        status="SANDBOX",
        total_units=ZERO,
        net_asset_value=ZERO,
        nav_per_unit=ONE,
    )
    db.add(fund)
    db.flush()
    return fund


def record_simulated_subscription(
    db: Session,
    *,
    fund: ManagedFund,
    subscriber_id: int,
    amount,
    reference: str,
    administrator: str,
) -> FundInvestorAccount:
    controls = assert_safe_configuration()
    if not controls["platform_enabled"] or not controls["simulated_execution"]:
        raise RuntimeError("Simulated fund execution is disabled")
    if fund.status != "SANDBOX":
        raise RuntimeError("Only sandbox funds are supported")

    existing_reference = (
        db.query(FundLedgerEntry)
        .filter(FundLedgerEntry.reference == reference)
        .first()
    )
    if existing_reference:
        raise ValueError("Ledger reference already exists")

    account = (
        db.query(FundInvestorAccount)
        .filter(
            FundInvestorAccount.fund_id == fund.id,
            FundInvestorAccount.subscriber_id == subscriber_id,
        )
        .first()
    )
    if account is None:
        account = FundInvestorAccount(
            fund_id=fund.id,
            subscriber_id=subscriber_id,
            high_water_mark_nav=money(fund.nav_per_unit),
        )
        db.add(account)
        db.flush()

    contribution = money(amount)
    issued_units = calculate_subscription_units(contribution, fund.nav_per_unit)
    account.units = units(decimal_value(account.units) + issued_units)
    account.contributed_capital = money(
        decimal_value(account.contributed_capital) + contribution
    )
    fund.total_units = units(decimal_value(fund.total_units) + issued_units)
    fund.net_asset_value = money(decimal_value(fund.net_asset_value) + contribution)
    fund.nav_per_unit = money(fund.net_asset_value / fund.total_units)

    db.add(FundLedgerEntry(
        fund_id=fund.id,
        investor_account_id=account.id,
        entry_type="SIMULATED_SUBSCRIPTION",
        amount=contribution,
        units=issued_units,
        nav_per_unit=fund.nav_per_unit,
        reference=reference,
        description="Sandbox capital subscription; no money received",
        created_by=administrator,
    ))
    return account


def record_valuation(
    db: Session,
    *,
    fund: ManagedFund,
    gross_assets,
    liabilities,
    valuation_at: datetime,
    administrator: str,
) -> FundValuation:
    controls = assert_safe_configuration()
    if not controls["platform_enabled"] or not controls["simulated_execution"]:
        raise RuntimeError("Simulated fund execution is disabled")
    net_assets, nav_per_unit = calculate_nav(
        gross_assets,
        liabilities,
        fund.total_units,
    )
    valuation = FundValuation(
        fund_id=fund.id,
        valuation_at=valuation_at,
        gross_assets=money(gross_assets),
        liabilities=money(liabilities),
        net_asset_value=net_assets,
        total_units=units(fund.total_units),
        nav_per_unit=nav_per_unit,
        source="SIMULATED",
        created_by=administrator,
    )
    fund.net_asset_value = net_assets
    fund.nav_per_unit = nav_per_unit
    db.add(valuation)
    db.flush()
    return valuation


def crystallize_profit_share(
    db: Session,
    *,
    fund: ManagedFund,
    period_start: datetime,
    period_end: datetime,
    administrator: str,
) -> ProfitSharePeriod:
    controls = assert_safe_configuration()
    if not controls["platform_enabled"] or not controls["simulated_execution"]:
        raise RuntimeError("Simulated fund execution is disabled")
    if period_end <= period_start:
        raise ValueError("Period end must be after period start")

    period = ProfitSharePeriod(
        fund_id=fund.id,
        period_start=period_start,
        period_end=period_end,
        closing_nav_per_unit=money(fund.nav_per_unit),
        created_by=administrator,
    )
    db.add(period)
    db.flush()

    total_gross = ZERO
    total_investor = ZERO
    total_fee = ZERO
    accounts = (
        db.query(FundInvestorAccount)
        .filter(
            FundInvestorAccount.fund_id == fund.id,
            FundInvestorAccount.status == "ACTIVE",
        )
        .all()
    )
    for account in accounts:
        allocation = calculate_profit_share(
            account_units=account.units,
            closing_nav_per_unit=fund.nav_per_unit,
            high_water_mark_nav=account.high_water_mark_nav,
            fee_rate=fund.performance_fee_rate,
        )
        total_gross += allocation["gross_eligible_profit"]
        total_investor += allocation["investor_profit"]
        total_fee += allocation["performance_fee"]
        db.add(InvestorProfitAllocation(
            period_id=period.id,
            investor_account_id=account.id,
            opening_high_water_mark_nav=money(account.high_water_mark_nav),
            closing_nav_per_unit=money(fund.nav_per_unit),
            units=units(account.units),
            **allocation,
        ))
        account.accrued_investor_profit = money(
            decimal_value(account.accrued_investor_profit)
            + allocation["investor_profit"]
        )
        account.accrued_performance_fee = money(
            decimal_value(account.accrued_performance_fee)
            + allocation["performance_fee"]
        )
        if allocation["gross_eligible_profit"] > ZERO:
            account.high_water_mark_nav = money(fund.nav_per_unit)

    period.gross_eligible_profit = money(total_gross)
    period.investor_profit = money(total_investor)
    period.performance_fee = money(total_fee)
    return period


def request_redemption(
    db: Session,
    *,
    account: FundInvestorAccount,
    fund: ManagedFund,
    requested_units,
    reason: str | None,
) -> FundRedemptionRequest:
    controls = assert_safe_configuration()
    if not controls["platform_enabled"]:
        raise RuntimeError("Fund platform is disabled")
    requested = units(requested_units)
    if requested <= ZERO:
        raise ValueError("Requested units must be positive")
    if requested > decimal_value(account.units):
        raise ValueError("Requested units exceed available units")
    redemption = FundRedemptionRequest(
        fund_id=fund.id,
        investor_account_id=account.id,
        requested_units=requested,
        estimated_nav_per_unit=money(fund.nav_per_unit),
        estimated_amount=money(requested * decimal_value(fund.nav_per_unit)),
        status="PENDING_SANDBOX",
        reason=reason,
    )
    db.add(redemption)
    db.flush()
    return redemption
