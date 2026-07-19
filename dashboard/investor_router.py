"""
Bethel Trading Technologies
Investor Performance Router

Public Investor Dashboard API
"""


from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from mt5_connector.account import MT5Account
from pathlib import Path


from mt5_connector.history import MT5History

from analytics.performance import PerformanceAnalytics

from analytics.equity_curve import EquityCurve



router = APIRouter(

    prefix="/investor",

    tags=["Investor"]

)



# ==================================
# INVESTOR PAGE
# ==================================


@router.get("/", response_class=HTMLResponse)

def investor_page():


    file_path = Path(

        "dashboard/templates/investor.html"

    )


    if file_path.exists():


        return file_path.read_text(

            encoding="utf-8"

        )


    return """

    <h1>
    Investor Dashboard Not Found
    </h1>

    """





# ==================================
# PUBLIC INVESTOR PERFORMANCE API
# ==================================


@router.get("/api/performance")

def investor_performance():


    history = MT5History().get_history()



    analytics = PerformanceAnalytics(

        history

    )



    return {


        "status":

        "success",



        "performance":

        analytics.calculate()

    }





# ==================================
# PUBLIC INVESTOR EQUITY API
# ==================================


@router.get("/api/equity")

def investor_equity():


    history = MT5History().get_history()



    engine = EquityCurve(

        history,

        starting_balance=100000

    )



    return {


        "status":

        "success",



        "equity":

        engine.calculate()

    }





# ==================================
# PUBLIC INVESTOR RISK API
# ==================================


@router.get("/api/risk")

def investor_risk():


    history = MT5History().get_history()



    total_trades = len(history)



    return {


        "status":

        "success",



        "risk": {


            "level":

            "LOW",



            "total_trades":

            total_trades


        }

    }


# ==================================
# MT5 ACCOUNT VERIFICATION
# ==================================


@router.get("/api/mt5")
def investor_mt5():

    try:

        account = MT5Account().get_account_info()

        if not account:

            return {
                "status":"offline",
                "login":"--",
                "server":"--",
                "currency":"--",
                "leverage":"--"
            }

        return {
            "status":"connected",
            "login":account.get("login","--"),
            "server":account.get("server","--"),
            "currency":account.get("currency","--"),
            "leverage":account.get("leverage","--")
        }

    except Exception as e:

        return {
            "status":"error",
            "message":str(e)
        }
