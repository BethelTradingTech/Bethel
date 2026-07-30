from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin
from api.database import get_db
from api.fund_management.accounting import decimal_value
from api.fund_management.config import assert_safe_configuration, fund_controls
from api.fund_management.models import (
    FundInvestorAccount,
    FundLedgerEntry,
    FundRedemptionRequest,
    FundValuation,
    InvestorProfitAllocation,
    ManagedFund,
    ProfitSharePeriod,
)
from api.fund_management.service import (
    create_fund,
    crystallize_profit_share,
    record_simulated_subscription,
    record_valuation,
    request_redemption,
)


router = APIRouter(prefix="/fund-management", tags=["Fund Management Sandbox"])


class FundCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    performance_fee_rate: float = Field(default=0.20, ge=0, le=1)


class SubscriptionRequest(BaseModel):
    subscriber_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    reference: str = Field(min_length=4, max_length=150)


class ValuationRequest(BaseModel):
    gross_assets: float = Field(ge=0)
    liabilities: float = Field(default=0, ge=0)
    valuation_at: datetime = Field(default_factory=datetime.utcnow)


class ProfitPeriodRequest(BaseModel):
    period_start: datetime
    period_end: datetime


class RedemptionRequest(BaseModel):
    requested_units: float = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)


class RedemptionReviewRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    reason: str | None = Field(default=None, max_length=500)


def _admin_name(admin: dict) -> str:
    return str(admin.get("email") or admin.get("sub") or "admin")


def _enabled_controls() -> dict:
    try:
        controls = assert_safe_configuration()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not controls["platform_enabled"]:
        raise HTTPException(status_code=503, detail="Fund platform is disabled")
    return controls


def _fund(db: Session, fund_id: int) -> ManagedFund:
    fund = db.query(ManagedFund).filter(ManagedFund.id == fund_id).first()
    if fund is None:
        raise HTTPException(status_code=404, detail="Fund not found")
    return fund


def _account(db: Session, fund_id: int, subscriber_id: int) -> FundInvestorAccount:
    account = (
        db.query(FundInvestorAccount)
        .filter(
            FundInvestorAccount.fund_id == fund_id,
            FundInvestorAccount.subscriber_id == subscriber_id,
        )
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Fund investor account not found")
    return account


def _fund_payload(fund: ManagedFund) -> dict:
    return {
        "id": fund.id,
        "name": fund.name,
        "currency": fund.currency,
        "status": fund.status,
        "valuation_frequency": fund.valuation_frequency,
        "distribution_frequency": fund.distribution_frequency,
        "performance_fee_rate": str(fund.performance_fee_rate),
        "total_units": str(fund.total_units),
        "net_asset_value": str(fund.net_asset_value),
        "nav_per_unit": str(fund.nav_per_unit),
    }


@router.get("/status")
def platform_status(_admin=Depends(require_admin)):
    controls = fund_controls()
    return {
        "mode": "SANDBOX_ONLY",
        "controls": controls,
        "live_operations_locked": not any(
            (
                controls["live_deposits"],
                controls["live_trading"],
                controls["live_withdrawals"],
            )
        ),
    }


@router.post("/admin/funds")
def admin_create_fund(
    data: FundCreateRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    _enabled_controls()
    try:
        fund = create_fund(
            db,
            name=data.name,
            currency=data.currency,
            performance_fee_rate=data.performance_fee_rate,
        )
        db.commit()
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Fund name already exists")
    db.refresh(fund)
    return {"status": "success", "fund": _fund_payload(fund)}


@router.get("/admin/funds")
def admin_list_funds(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    _enabled_controls()
    funds = db.query(ManagedFund).order_by(ManagedFund.created_at.desc()).all()
    return {"status": "success", "funds": [_fund_payload(fund) for fund in funds]}


@router.post("/admin/funds/{fund_id}/simulated-subscriptions")
def admin_simulated_subscription(
    fund_id: int,
    data: SubscriptionRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    _enabled_controls()
    fund = _fund(db, fund_id)
    try:
        account = record_simulated_subscription(
            db,
            fund=fund,
            subscriber_id=data.subscriber_id,
            amount=data.amount,
            reference=data.reference,
            administrator=_admin_name(admin),
        )
        db.commit()
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    db.refresh(account)
    return {
        "status": "success",
        "notice": "Sandbox ledger only; no investor money was received",
        "account": {
            "fund_id": account.fund_id,
            "subscriber_id": account.subscriber_id,
            "units": str(account.units),
            "contributed_capital": str(account.contributed_capital),
            "high_water_mark_nav": str(account.high_water_mark_nav),
        },
    }


@router.post("/admin/funds/{fund_id}/valuations")
def admin_record_valuation(
    fund_id: int,
    data: ValuationRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    _enabled_controls()
    fund = _fund(db, fund_id)
    try:
        valuation = record_valuation(
            db,
            fund=fund,
            gross_assets=data.gross_assets,
            liabilities=data.liabilities,
            valuation_at=data.valuation_at,
            administrator=_admin_name(admin),
        )
        db.commit()
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    db.refresh(valuation)
    return {
        "status": "success",
        "valuation": {
            "id": valuation.id,
            "valuation_at": valuation.valuation_at.isoformat(),
            "net_asset_value": str(valuation.net_asset_value),
            "nav_per_unit": str(valuation.nav_per_unit),
            "source": valuation.source,
        },
    }


@router.post("/admin/funds/{fund_id}/profit-periods")
def admin_crystallize_profit_period(
    fund_id: int,
    data: ProfitPeriodRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    _enabled_controls()
    fund = _fund(db, fund_id)
    try:
        period = crystallize_profit_share(
            db,
            fund=fund,
            period_start=data.period_start,
            period_end=data.period_end,
            administrator=_admin_name(admin),
        )
        db.commit()
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Profit period already exists")
    db.refresh(period)
    return {
        "status": "success",
        "notice": "Sandbox accrual only; no profit was paid",
        "period": {
            "id": period.id,
            "gross_eligible_profit": str(period.gross_eligible_profit),
            "investor_profit": str(period.investor_profit),
            "performance_fee": str(period.performance_fee),
            "status": period.status,
        },
    }


@router.get("/funds/{fund_id}/investors/{subscriber_id}/statement")
def investor_statement(
    fund_id: int,
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    _enabled_controls()
    fund = _fund(db, fund_id)
    account = _account(db, fund_id, subscriber_id)
    allocations = (
        db.query(InvestorProfitAllocation)
        .filter(InvestorProfitAllocation.investor_account_id == account.id)
        .order_by(InvestorProfitAllocation.created_at.desc())
        .all()
    )
    ledger = (
        db.query(FundLedgerEntry)
        .filter(FundLedgerEntry.investor_account_id == account.id)
        .order_by(FundLedgerEntry.created_at.desc())
        .all()
    )
    estimated_value = decimal_value(account.units) * decimal_value(fund.nav_per_unit)
    return {
        "mode": "SANDBOX_ONLY",
        "fund": _fund_payload(fund),
        "account": {
            "subscriber_id": subscriber_id,
            "units": str(account.units),
            "contributed_capital": str(account.contributed_capital),
            "estimated_value": str(estimated_value),
            "high_water_mark_nav": str(account.high_water_mark_nav),
            "accrued_investor_profit": str(account.accrued_investor_profit),
            "accrued_performance_fee": str(account.accrued_performance_fee),
        },
        "profit_allocations": [
            {
                "period_id": row.period_id,
                "gross_eligible_profit": str(row.gross_eligible_profit),
                "investor_profit": str(row.investor_profit),
                "performance_fee": str(row.performance_fee),
                "status": row.status,
            }
            for row in allocations
        ],
        "ledger": [
            {
                "entry_type": row.entry_type,
                "amount": str(row.amount),
                "units": str(row.units) if row.units is not None else None,
                "reference": row.reference,
                "created_at": row.created_at.isoformat(),
            }
            for row in ledger
        ],
    }


@router.post("/funds/{fund_id}/investors/{subscriber_id}/redemptions")
def investor_request_redemption(
    fund_id: int,
    subscriber_id: int,
    data: RedemptionRequest,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    _enabled_controls()
    fund = _fund(db, fund_id)
    account = _account(db, fund_id, subscriber_id)
    try:
        redemption = request_redemption(
            db,
            account=account,
            fund=fund,
            requested_units=data.requested_units,
            reason=data.reason,
        )
        db.commit()
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    db.refresh(redemption)
    return {
        "status": "success",
        "notice": "Request recorded in sandbox; no withdrawal will execute",
        "redemption": {
            "id": redemption.id,
            "requested_units": str(redemption.requested_units),
            "estimated_amount": str(redemption.estimated_amount),
            "status": redemption.status,
        },
    }


@router.post("/admin/redemptions/{redemption_id}/review")
def admin_review_redemption(
    redemption_id: int,
    data: RedemptionReviewRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    controls = _enabled_controls()
    redemption = (
        db.query(FundRedemptionRequest)
        .filter(FundRedemptionRequest.id == redemption_id)
        .first()
    )
    if redemption is None:
        raise HTTPException(status_code=404, detail="Redemption request not found")
    redemption.status = f"{data.decision}_SANDBOX"
    redemption.reason = data.reason or redemption.reason
    redemption.reviewed_by = _admin_name(admin)
    redemption.reviewed_at = datetime.utcnow()
    db.commit()
    return {
        "status": "success",
        "notice": (
            "Administrative review recorded. Live withdrawals remain locked."
            if not controls["live_withdrawals"]
            else "Live withdrawal configuration is invalid for this release."
        ),
        "redemption_status": redemption.status,
    }
