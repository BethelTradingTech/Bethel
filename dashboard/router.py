"""
Bethel Trading Technologies
Dashboard Router

Provides dashboard data:
- MT5 account
- Positions
- Statistics
"""

from fastapi import APIRouter
from datetime import datetime

from mt5_connector.account import MT5Account
from mt5_connector.positions import MT5Positions


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/data")
def dashboard_data():

    try:

        account = MT5Account()
        account_info = account.get_account()


        positions = MT5Positions()
        open_positions = positions.get_positions()


        return {

            "platform": "Bethel Trading Technologies",

            "status": "ONLINE",

            "timestamp": datetime.utcnow(),

            "account": account_info,

            "positions": open_positions,

            "analytics": {

                "total_positions": len(open_positions),

                "risk_status": "ACTIVE"

            }

        }


    except Exception as e:

        return {

            "platform": "Bethel Trading Technologies",

            "status": "ERROR",

            "message": str(e)

        }



@router.get("/")
def dashboard_home():

    return {

        "message": "Bethel Trading Technologies Dashboard",

        "status": "running",

        "modules": [

            "MT5 Connection",

            "Account Analytics",

            "Risk Engine",

            "Trade History"

        ]

    }