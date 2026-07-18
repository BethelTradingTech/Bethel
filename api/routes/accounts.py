from fastapi import APIRouter

router = APIRouter(
    prefix="/accounts",
    tags=["Trading Accounts"]
)


@router.get("/")
def get_accounts():

    return {
        "accounts": [
            {
                "id": 1,
                "broker": "Demo Broker",
                "account_number": "123456",
                "status": "connected"
            }
        ]
    }