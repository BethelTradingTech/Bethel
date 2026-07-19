from fastapi import APIRouter
from mt5_connector.account import MT5Account


router = APIRouter(
    prefix="/investor",
    tags=["Investor"]
)


@router.get("/api/mt5")
def investor_mt5():

    try:

        account = MT5Account().get_account_info()

        if not account:
            return {
                "status": "offline",
                "login": "--",
                "server": "--",
                "currency": "--",
                "leverage": "--"
            }


        return {
            "status": "connected",
            "login": account.get("login", "--"),
            "server": account.get("server", "--"),
            "currency": account.get("currency", "--"),
            "leverage": account.get("leverage", "--")
        }


    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }