from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin
from api.database import get_db
from api.investors.models import Investor, Portfolio
from api.models import MT5Account


router = APIRouter(
    prefix="/admin/investors",
    tags=["Admin Investors"],
    dependencies=[Depends(require_admin)],
)


def investor_summary(db: Session, investor: Investor):
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.investor_id == investor.id)
        .first()
    )
    account = (
        db.query(MT5Account)
        .filter(MT5Account.investor_id == investor.id)
        .first()
    )

    return {
        "id": investor.id,
        "name": investor.name,
        "email": investor.email,
        "phone": investor.phone,
        "country": investor.country,
        "status": investor.status,
        "capital": investor.capital,
        "portfolio": {
            "id": portfolio.id if portfolio else None,
            "name": portfolio.portfolio_name if portfolio else None,
            "starting_capital": portfolio.starting_capital if portfolio else 0,
            "current_value": portfolio.current_value if portfolio else 0,
            "total_return": portfolio.total_return if portfolio else 0,
            "status": portfolio.status if portfolio else None,
        },
        "mt5": {
            "login": account.mt5_login if account else None,
            "server": account.server if account else None,
            "currency": account.currency if account else None,
        },
    }


@router.get("")
def list_investors(db: Session = Depends(get_db)):
    investors = db.query(Investor).order_by(Investor.id).all()
    return {
        "count": len(investors),
        "investors": [investor_summary(db, investor) for investor in investors],
    }


@router.get("/{investor_id}")
def get_investor(investor_id: int, db: Session = Depends(get_db)):
    investor = (
        db.query(Investor)
        .filter(Investor.id == investor_id)
        .first()
    )
    if investor is None:
        raise HTTPException(status_code=404, detail="Investor not found")
    return investor_summary(db, investor)
