"""
Bethel Trading Technologies
MT5 Investor Account Assignment API
"""


from fastapi import APIRouter, HTTPException

from api.database import SessionLocal

from api.investors.mt5_account import MT5Account



router = APIRouter(

    prefix="/mt5-accounts",

    tags=["MT5 Accounts"]

)





# ======================================
# ASSIGN MT5 ACCOUNT
# ======================================


@router.post("/assign")
def assign_account(

    investor_id:int,

    portfolio_id:int,

    mt5_login:str,

    broker:str,

    server:str,

    currency:str="USD",

    initial_balance:float=0

):


    db = SessionLocal()



    account = MT5Account(

        investor_id=investor_id,

        portfolio_id=portfolio_id,

        mt5_login=mt5_login,

        broker=broker,

        server=server,

        currency=currency,

        initial_balance=initial_balance,

        current_balance=initial_balance,

        current_equity=initial_balance

    )


    db.add(account)

    db.commit()

    db.refresh(account)


    db.close()



    return {


        "status":"success",

        "account_id":account.id,

        "mt5_login":account.mt5_login,

        "server":account.server

    }





# ======================================
# GET INVESTOR MT5 ACCOUNTS
# ======================================


@router.get("/{investor_id}")
def get_accounts(

    investor_id:int

):


    db = SessionLocal()


    accounts = db.query(MT5Account).filter(

        MT5Account.investor_id == investor_id

    ).all()



    db.close()



    return {


        "status":"success",

        "investor_id":investor_id,

        "accounts":[


            {


                "id":a.id,

                "login":a.mt5_login,

                "server":a.server,

                "currency":a.currency,

                "equity":a.current_equity,

                "status":a.status


            }


            for a in accounts


        ]

    }