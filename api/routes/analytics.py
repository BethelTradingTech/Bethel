"""
Bethel Trading Technologies
Analytics API Routes

Provides:
- Performance statistics
- Equity curve calculation
- Protected analytics endpoints
"""


from fastapi import APIRouter, Request


from mt5_connector.history import MT5History


from analytics.performance import PerformanceAnalytics

from analytics.equity_curve import EquityCurve


from api.auth.dependency import check_auth




router = APIRouter(

    prefix="/analytics",

    tags=["Analytics"]

)





# =====================================================
# PERFORMANCE ANALYTICS
# =====================================================


@router.get("/performance")
def performance(

    request: Request

):


    # -------------------------
    # AUTHENTICATION
    # -------------------------

    auth = check_auth(request)


    if auth:

        return auth



    try:


        # -------------------------
        # GET MT5 HISTORY
        # -------------------------

        history = MT5History().get_history()



        # -------------------------
        # RUN ANALYTICS ENGINE
        # -------------------------

        analytics = PerformanceAnalytics(

            history

        )


        result = analytics.calculate()



        return {


            "status": "success",


            "performance": result


        }



    except Exception as e:


        return {


            "status": "error",


            "message": str(e)


        }








# =====================================================
# EQUITY CURVE
# =====================================================


@router.get("/equity")
def equity_curve(

    request: Request

):


    # -------------------------
    # AUTHENTICATION
    # -------------------------

    auth = check_auth(request)


    if auth:

        return auth




    try:


        # -------------------------
        # GET HISTORY
        # -------------------------

        history = MT5History().get_history()




        # -------------------------
        # BUILD EQUITY CURVE
        # -------------------------

        engine = EquityCurve(

            history,

            starting_balance=100000

        )



        return {


            "status": "success",


            "equity": engine.calculate()


        }




    except Exception as e:



        return {


            "status": "error",


            "message": str(e)


        }








# =====================================================
# ANALYTICS HEALTH CHECK
# =====================================================


@router.get("/status")
def analytics_status():


    return {


        "module": "Analytics Engine",


        "status": "online",


        "company":

        "Bethel Trading Technologies"


    }