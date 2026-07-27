import calendar
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.onboarding.models import ClientOnboarding
from api.onboarding.service import recompute_activation
from api.profit_share.models import (
    ProfitShareAccount,
    ProfitShareAgreement,
    ProfitShareAudit,
    ProfitShareStatement,
)
from api.profit_share.service import (
    AGREEMENT_VERSION,
    FEE_RATE,
    calculate_statement,
    create_account,
    profit_share_accepted,
    projected_accrual,
    statement_dict,
)


router = APIRouter(tags=["20 Percent Profit Share"])


class AgreementAcceptance(BaseModel):
    accepted: bool


class StatementStatus(BaseModel):
    status: str


def previous_month():
    now = datetime.utcnow()
    if now.month == 1:
        year, month = now.year - 1, 12
    else:
        year, month = now.year, now.month - 1
    return (
        datetime(year, month, 1),
        datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59, 999999),
    )


@router.get("/profit-share/terms")
def profit_share_terms():
    return {
        "version": AGREEMENT_VERSION,
        "fee_rate": FEE_RATE,
        "fee_percent": 20,
        "subscriber_percent": 80,
        "calculation_basis": "Closed realized net profit above the high-water mark",
        "crystallization": "Monthly after administrator review",
        "loss_policy": "Losses carry forward; recovered losses are not charged again",
        "collection": "Statement only; no automatic withdrawal",
    }


@router.post("/profit-share/{subscriber_id}/accept")
def accept_profit_share(
    subscriber_id: int,
    data: AgreementAcceptance,
    request: Request,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    if not data.accepted:
        raise HTTPException(status_code=422, detail="Explicit acceptance is required")
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    agreement = (
        db.query(ProfitShareAgreement)
        .filter(ProfitShareAgreement.subscriber_id == subscriber_id)
        .first()
    )
    now = datetime.utcnow()
    if agreement is None:
        agreement = ProfitShareAgreement(
            subscriber_id=subscriber_id,
            version=AGREEMENT_VERSION,
            fee_rate=FEE_RATE,
            accepted_at=now,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(agreement)
        db.flush()
    elif agreement.version != AGREEMENT_VERSION or agreement.revoked_at:
        agreement.version = AGREEMENT_VERSION
        agreement.fee_rate = FEE_RATE
        agreement.accepted_at = now
        agreement.revoked_at = None
        agreement.ip_address = request.client.host if request.client else None
        agreement.user_agent = request.headers.get("user-agent")
    create_account(db, subscriber_id, agreement.accepted_at)
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding:
        recompute_activation(db, onboarding)
    db.commit()
    return {
        "status": "accepted",
        "version": agreement.version,
        "accepted_at": agreement.accepted_at.isoformat(),
    }


@router.get("/profit-share/{subscriber_id}")
def subscriber_profit_share(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    account = (
        db.query(ProfitShareAccount)
        .filter(ProfitShareAccount.subscriber_id == subscriber_id)
        .first()
    )
    statements = (
        db.query(ProfitShareStatement)
        .filter(ProfitShareStatement.subscriber_id == subscriber_id)
        .order_by(ProfitShareStatement.period_end.desc())
        .all()
    )
    return {
        "accepted": profit_share_accepted(db, subscriber_id),
        "agreement_version": AGREEMENT_VERSION,
        "fee_percent": 20,
        "account": (
            {
                "fee_start_at": account.fee_start_at.isoformat(),
                **projected_accrual(db, account),
            }
            if account else None
        ),
        "statements": [statement_dict(row) for row in statements],
    }


@router.get("/admin/profit-share")
def admin_profit_share(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    subscribers = {row.id: row for row in db.query(CopySubscriber).all()}
    accounts = db.query(ProfitShareAccount).all()
    rows = []
    for account in accounts:
        subscriber = subscribers.get(account.subscriber_id)
        rows.append({
            "subscriber_id": account.subscriber_id,
            "subscriber_name": getattr(subscriber, "name", None),
            "subscriber_email": getattr(subscriber, "email", None),
            "fee_start_at": account.fee_start_at.isoformat(),
            **projected_accrual(db, account),
        })
    outstanding = (
        db.query(ProfitShareStatement)
        .filter(ProfitShareStatement.status.in_(("FINALIZED", "INVOICED")))
        .all()
    )
    outstanding_by_currency = {}
    for statement in outstanding:
        outstanding_by_currency[statement.currency] = round(
            outstanding_by_currency.get(statement.currency, 0.0) + statement.fee_due,
            2,
        )
    return {
        "status": "success",
        "fee_percent": 20,
        "accounts": rows,
        "outstanding_fees_by_currency": outstanding_by_currency,
    }


@router.post("/admin/profit-share/{subscriber_id}/generate")
def generate_statement(
    subscriber_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    account = (
        db.query(ProfitShareAccount)
        .filter(ProfitShareAccount.subscriber_id == subscriber_id)
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Profit-share account not found")
    period_start, period_end = previous_month()
    if period_end < account.fee_start_at:
        raise HTTPException(
            status_code=409,
            detail="No completed monthly period exists after agreement acceptance",
        )
    period_start = max(period_start, account.fee_start_at)
    statement = calculate_statement(db, account, period_start, period_end)
    db.add(ProfitShareAudit(
        subscriber_id=subscriber_id,
        statement_id=statement.id,
        action="GENERATE",
        administrator=str(admin.get("email") or admin.get("sub") or "admin"),
        details=json.dumps(statement_dict(statement)),
    ))
    db.commit()
    return {"status": "success", "statement": statement_dict(statement)}


@router.post("/admin/profit-share/statements/{statement_id}/finalize")
def finalize_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    statement = (
        db.query(ProfitShareStatement)
        .filter(ProfitShareStatement.id == statement_id)
        .first()
    )
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    if statement.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only draft statements can be finalized")
    account = (
        db.query(ProfitShareAccount)
        .filter(ProfitShareAccount.subscriber_id == statement.subscriber_id)
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Profit-share account not found")
    statement.status = "FINALIZED"
    statement.finalized_at = datetime.utcnow()
    account.high_water_mark = statement.new_high_water_mark
    account.last_crystallized_at = statement.period_end
    db.add(ProfitShareAudit(
        subscriber_id=statement.subscriber_id,
        statement_id=statement.id,
        action="FINALIZE",
        administrator=str(admin.get("email") or admin.get("sub") or "admin"),
    ))
    db.commit()
    return {"status": "success", "statement": statement_dict(statement)}


@router.post("/admin/profit-share/statements/{statement_id}/status")
def change_statement_status(
    statement_id: int,
    data: StatementStatus,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    new_status = data.status.upper()
    if new_status not in ("INVOICED", "PAID", "WAIVED"):
        raise HTTPException(status_code=422, detail="Invalid statement status")
    statement = (
        db.query(ProfitShareStatement)
        .filter(ProfitShareStatement.id == statement_id)
        .first()
    )
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    if statement.status not in ("FINALIZED", "INVOICED"):
        raise HTTPException(status_code=409, detail="Statement must be finalized first")
    previous = statement.status
    statement.status = new_status
    statement.paid_at = datetime.utcnow() if new_status == "PAID" else None
    db.add(ProfitShareAudit(
        subscriber_id=statement.subscriber_id,
        statement_id=statement.id,
        action=f"{previous}_TO_{new_status}",
        administrator=str(admin.get("email") or admin.get("sub") or "admin"),
    ))
    db.commit()
    return {"status": "success", "statement": statement_dict(statement)}
