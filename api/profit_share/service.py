from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.copytrading.models import CopyTradePerformance
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.profit_share.models import (
    ProfitShareAccount,
    ProfitShareAgreement,
    ProfitShareStatement,
)


AGREEMENT_VERSION = "BTT-PROFIT-SHARE-20-V1"
FEE_RATE = 0.20


def realized_profit_through(db: Session, subscriber_id: int, end: datetime) -> float:
    value = (
        db.query(func.coalesce(func.sum(CopyTradePerformance.profit_loss), 0.0))
        .filter(
            CopyTradePerformance.subscriber_id == subscriber_id,
            CopyTradePerformance.closed_at.isnot(None),
            CopyTradePerformance.closed_at <= end,
            func.upper(CopyTradePerformance.status) != "OPEN",
        )
        .scalar()
    )
    return round(float(value or 0.0), 2)


def profit_share_accepted(db: Session, subscriber_id: int) -> bool:
    agreement = (
        db.query(ProfitShareAgreement)
        .filter(
            ProfitShareAgreement.subscriber_id == subscriber_id,
            ProfitShareAgreement.version == AGREEMENT_VERSION,
            ProfitShareAgreement.revoked_at.is_(None),
        )
        .first()
    )
    return agreement is not None


def create_account(db: Session, subscriber_id: int, accepted_at: datetime):
    account = (
        db.query(ProfitShareAccount)
        .filter(ProfitShareAccount.subscriber_id == subscriber_id)
        .first()
    )
    if account:
        return account
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.id == getattr(onboarding, "plan_id", None))
        .first()
    )
    baseline = realized_profit_through(db, subscriber_id, accepted_at)
    account = ProfitShareAccount(
        subscriber_id=subscriber_id,
        fee_rate=FEE_RATE,
        currency=getattr(plan, "currency", None) or "USD",
        fee_start_at=accepted_at,
        baseline_cumulative_profit=baseline,
        high_water_mark=0.0,
    )
    db.add(account)
    db.flush()
    return account


def projected_accrual(db: Session, account: ProfitShareAccount, end=None):
    end = end or datetime.utcnow()
    total = realized_profit_through(db, account.subscriber_id, end)
    net_since_enrollment = round(total - account.baseline_cumulative_profit, 2)
    eligible = round(max(0.0, net_since_enrollment - account.high_water_mark), 2)
    fee = round(eligible * account.fee_rate, 2)
    return {
        "cumulative_net_profit": net_since_enrollment,
        "high_water_mark": account.high_water_mark,
        "eligible_profit": eligible,
        "projected_fee": fee,
        "subscriber_profit_share": round(eligible - fee, 2),
        "fee_rate": account.fee_rate,
        "currency": account.currency,
    }


def calculate_statement(
    db: Session,
    account: ProfitShareAccount,
    period_start: datetime,
    period_end: datetime,
):
    existing = (
        db.query(ProfitShareStatement)
        .filter(
            ProfitShareStatement.subscriber_id == account.subscriber_id,
            ProfitShareStatement.period_start == period_start,
            ProfitShareStatement.period_end == period_end,
        )
        .first()
    )
    if existing:
        return existing
    projection = projected_accrual(db, account, period_end)
    statement = ProfitShareStatement(
        subscriber_id=account.subscriber_id,
        period_start=period_start,
        period_end=period_end,
        cumulative_net_profit=projection["cumulative_net_profit"],
        previous_high_water_mark=account.high_water_mark,
        eligible_profit=projection["eligible_profit"],
        fee_rate=account.fee_rate,
        fee_due=projection["projected_fee"],
        subscriber_profit_share=projection["subscriber_profit_share"],
        new_high_water_mark=max(
            account.high_water_mark,
            projection["cumulative_net_profit"],
        ),
        currency=account.currency,
        status="DRAFT",
    )
    db.add(statement)
    db.flush()
    return statement


def statement_dict(statement: ProfitShareStatement):
    return {
        "id": statement.id,
        "subscriber_id": statement.subscriber_id,
        "period_start": statement.period_start.isoformat(),
        "period_end": statement.period_end.isoformat(),
        "cumulative_net_profit": statement.cumulative_net_profit,
        "previous_high_water_mark": statement.previous_high_water_mark,
        "eligible_profit": statement.eligible_profit,
        "fee_rate": statement.fee_rate,
        "fee_percent": round(statement.fee_rate * 100, 2),
        "fee_due": statement.fee_due,
        "subscriber_profit_share": statement.subscriber_profit_share,
        "new_high_water_mark": statement.new_high_water_mark,
        "currency": statement.currency,
        "status": statement.status,
        "created_at": statement.created_at.isoformat(),
        "finalized_at": statement.finalized_at.isoformat() if statement.finalized_at else None,
        "paid_at": statement.paid_at.isoformat() if statement.paid_at else None,
    }
