"""
Bethel Trading Technologies
Risk Dashboard API
Protected Route
"""


from fastapi import APIRouter, Request


from mt5_connector.account import MT5Account

from mt5_connector.positions import MT5Positions


from api.auth.dependency import check_auth



router = APIRouter(

    prefix="/risk",

    tags=["Risk"]

)



# ==========================
# RISK STATUS
# ==========================


@router.get("/status")
def risk_status(

    request: Request

):


    # ==========================
    # AUTHENTICATION CHECK
    # ==========================

    auth = check_auth(request)


    if auth:

        return auth



    # ==========================
    # GET MT5 ACCOUNT
    # ==========================

    account = MT5Account().get_account_info()



    # ==========================
    # GET OPEN POSITIONS
    # ==========================

    positions = MT5Positions().get_positions()



    if account.get("status") != "connected":

        return {

            "status": "failed",

            "message": "MT5 account unavailable"

        }



    balance = account.get(

        "balance",

        0

    )


    equity = account.get(

        "equity",

        0

    )


    profit = account.get(

        "profit",

        0

    )



    # ==========================
    # CALCULATE DRAWDOWN
    # ==========================

    drawdown = 0


    if balance > 0:


        drawdown = (

            (balance - equity)

            /

            balance

        ) * 100



    open_positions = positions.get(

        "count",

        0

    )



    # ==========================
    # RISK LEVEL
    # ==========================

    if drawdown < 5:

        risk_level = "LOW"


    elif drawdown < 10:

        risk_level = "MEDIUM"


    else:

        risk_level = "HIGH"



    # ==========================
    # RESPONSE
    # ==========================

    return {


        "status":

        "success",


        "risk": {


            "level":

            risk_level,


            "balance":

            balance,


            "equity":

            equity,


            "floating_profit":

            profit,


            "drawdown_percent":

            round(

                drawdown,

                2

            ),


            "open_positions":

            open_positions,


            "risk_score":

            round(

                max(

                    0,

                    10 - drawdown

                ),

                2

            )

        }

    }