"""
Bethel Trading Technologies
Dashboard Data API
Protected Route
"""


from fastapi import APIRouter, Request


from mt5_connector.account import MT5Account
from mt5_connector.positions import MT5Positions
from mt5_connector.history import MT5History


from analytics.performance import PerformanceAnalytics


from api.auth.dependency import check_auth



router = APIRouter(

    prefix="/dashboard",

    tags=["Dashboard"]

)



# ==========================
# DASHBOARD DATA
# ==========================


@router.get("/data")
def dashboard_data(

    request: Request

):


    # ==========================
    # AUTHENTICATION CHECK
    # ==========================

    auth = check_auth(request)


    if auth:

        return auth



    # ==========================
    # MT5 DATA MODULES
    # ==========================

    account = MT5Account()


    positions = MT5Positions()


    history = MT5History()



    # ==========================
    # GET LIVE DATA
    # ==========================

    account_data = account.get_account_info()


    positions_data = positions.get_positions()


    history_data = history.get_history()



    # ==========================
    # PERFORMANCE ANALYTICS
    # ==========================

    performance = PerformanceAnalytics(

        history_data

    ).calculate()



    # ==========================
    # DASHBOARD RESPONSE
    # ==========================

    return {


        "system": {


            "company":

            "Bethel Trading Technologies",


            "status":

            "online"


        },


        "account":

        account_data,


        "positions":

        positions_data,


        "history":

        history_data,


        "performance":

        performance

    }