"""
Bethel Trading Technologies
Investor Dashboard API
"""


from fastapi import APIRouter, HTTPException

from api.database import SessionLocal

from api.investors.models import Investor, Portfolio

from api.models import MT5Account


router = APIRouter(

    prefix="/investor/api",

    tags=["Investor Dashboard"]

)



@router.get("/dashboard/{investor_id}")
def investor_dashboard(

    investor_id:int

):


    db = SessionLocal()


    investor = db.query(Investor).filter(

        Investor.id == investor_id

    ).first()



    if not investor:

        db.close()

        raise HTTPException(

            status_code=404,

            detail="Investor not found"

        )



    portfolio = db.query(Portfolio).filter(

        Portfolio.investor_id == investor_id

    ).first()



    account = db.query(MT5Account).filter(

        MT5Account.investor_id == investor_id

    ).first()



    response = {


        "investor": {

            "id": investor.id,

            "name": investor.name,

            "email": investor.email

        },


        "portfolio": {

            "id": portfolio.id if portfolio else None,

            "name": portfolio.portfolio_name if portfolio else None,

            "capital": portfolio.starting_capital if portfolio else 0,

            "current_value": portfolio.current_value if portfolio else 0

        },


        "mt5": {

            "login": account.mt5_login if account else None,

            "server": account.server if account else None,

            "currency": account.currency if account else None

        }

    }


    db.close()


    return response