from fastapi import APIRouter

from api.schemas import MT5ConnectionRequest
from api.database import SessionLocal
from api.models import MT5Account as MT5AccountModel

from mt5_connector.connection import MT5Connection
from mt5_connector.account import MT5Account
from mt5_connector.positions import MT5Positions
from mt5_connector.orders import MT5Order
from mt5_connector.symbols import MT5Symbols
from mt5_connector.history import MT5History


router = APIRouter(
    prefix="/mt5",
    tags=["MT5 Connection"]
)


@router.post("/connect")
def connect_mt5(request: MT5ConnectionRequest):

    db = SessionLocal()

    try:

        existing = db.query(
            MT5AccountModel
        ).filter(
            MT5AccountModel.account_number == request.account_number
        ).first()


        if existing:

            account = existing
            account.server = request.server
            account.investor_password = request.password
            account.status = "CONNECTING"

        else:

            account = MT5AccountModel(
                account_number=request.account_number,
                server=request.server,
                investor_password=request.password,
                status="CONNECTING"
            )

            db.add(account)


        db.commit()
        db.refresh(account)


        connection = MT5Connection(
            account_number=request.account_number,
            server=request.server,
            password=request.password
        )


        result = connection.connect()


        if isinstance(result, dict):

            if result.get("status") == "connected":
                account.status = "CONNECTED"

            else:
                account.status = "FAILED"


        db.commit()

        return result


    finally:
        db.close()



@router.get("/account")
def account_info():

    account = MT5Account()

    return account.get_account_info()



@router.get("/positions")
def open_positions():

    positions = MT5Positions()

    return positions.get_positions()



@router.post("/test-order")
def test_order():

    order = MT5Order()

    return order.send_order(
        symbol="EURUSD",
        side="BUY",
        volume=0.01,
        stop_loss=None,
        take_profit=None
    )



@router.get("/symbols")
def get_symbols():

    symbols = MT5Symbols()

    return symbols.get_symbols()



@router.get("/history")
def trade_history():

    history = MT5History()

    return history.get_history()