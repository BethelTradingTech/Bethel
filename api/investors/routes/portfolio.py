"""
Bethel Trading Technologies
Portfolio Management API
"""


from fastapi import APIRouter, HTTPException

from api.database import SessionLocal

from api.investors.models import Portfolio



router = APIRouter(

    prefix="/portfolio",

    tags=["Portfolio"]

)





# ======================================
# CREATE PORTFOLIO
# ======================================


@router.post("/create")
def create_portfolio(

    investor_id:int,

    starting_capital:float

):


    db = SessionLocal()



    portfolio = Portfolio(

        investor_id=investor_id,

        starting_capital=starting_capital,

        current_value=starting_capital

    )


    db.add(portfolio)

    db.commit()

    db.refresh(portfolio)


    db.close()



    return {


        "status":"success",

        "portfolio_id":portfolio.id,

        "investor_id":portfolio.investor_id,

        "capital":portfolio.starting_capital

    }





# ======================================
# GET INVESTOR PORTFOLIOS
# ======================================


@router.get("/{investor_id}")
def get_portfolios(

    investor_id:int

):


    db = SessionLocal()


    portfolios = db.query(Portfolio).filter(

        Portfolio.investor_id == investor_id

    ).all()



    db.close()



    return {


        "status":"success",

        "investor_id":investor_id,

        "count":len(portfolios),

        "portfolios":[


            {


                "id":p.id,

                "name":p.portfolio_name,

                "starting_capital":p.starting_capital,

                "current_value":p.current_value,

                "return":p.total_return,

                "status":p.status


            }


            for p in portfolios


        ]

    }





# ======================================
# UPDATE PORTFOLIO VALUE
# ======================================


@router.put("/{portfolio_id}/update")
def update_portfolio(

    portfolio_id:int,

    current_value:float

):


    db = SessionLocal()



    portfolio = db.query(Portfolio).filter(

        Portfolio.id == portfolio_id

    ).first()



    if not portfolio:


        db.close()


        raise HTTPException(

            status_code=404,

            detail="Portfolio not found"

        )



    portfolio.current_value = current_value



    portfolio.total_return = (

        (

            current_value -

            portfolio.starting_capital

        )

        /

        portfolio.starting_capital

    ) * 100



    db.commit()


    db.refresh(portfolio)


    db.close()



    return {


        "status":"success",

        "portfolio_id":portfolio.id,

        "current_value":portfolio.current_value,

        "return_percent":portfolio.total_return

    }