"""
Bethel Trading Technologies
MT5 API Routes
Protected Routes
"""


from fastapi import APIRouter, Request


from api.schemas import MT5ConnectionRequest

from api.database import SessionLocal

from api.models import MT5Account as MT5AccountModel


from api.auth.dependency import check_auth


from api.services.trade_importer import import_mt5_history


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





# ==========================
# MT5 CONNECTION
# ==========================


@router.post("/connect")
def connect_mt5(

    request: Request,

    data: MT5ConnectionRequest

):


    auth = check_auth(request)


    if auth:

        return auth



    db = SessionLocal()


    try:


        existing = db.query(

            MT5AccountModel

        ).filter(

            MT5AccountModel.account_number == data.account_number

        ).first()



        if existing:


            account = existing


            account.server = data.server


            account.investor_password = data.password


            account.status = "CONNECTING"



        else:


            account = MT5AccountModel(

                account_number=data.account_number,

                server=data.server,

                investor_password=data.password,

                status="CONNECTING"

            )


            db.add(account)



        db.commit()


        db.refresh(account)



        connection = MT5Connection(


            account_number=data.account_number,

            server=data.server,

            password=data.password

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







# ==========================
# ACCOUNT INFORMATION
# ==========================


@router.get("/account")
def account_info(

    request: Request

):


    auth = check_auth(request)


    if auth:

        return auth



    account = MT5Account()


    return account.get_account_info()







# ==========================
# OPEN POSITIONS
# ==========================


@router.get("/positions")
def open_positions(

    request: Request

):


    auth = check_auth(request)


    if auth:

        return auth



    positions = MT5Positions()


    return positions.get_positions()







# ==========================
# TEST ORDER
# ==========================


@router.post("/test-order")
def test_order(

    request: Request

):


    auth = check_auth(request)


    if auth:

        return auth



    order = MT5Order()



    return order.send_order(

        symbol="EURUSD",

        side="BUY",

        volume=0.01,

        stop_loss=None,

        take_profit=None

    )









# ==========================
# SYMBOL LIST
# ==========================


@router.get("/symbols")
def get_symbols(

    request: Request

):


    auth = check_auth(request)


    if auth:

        return auth



    symbols = MT5Symbols()


    return symbols.get_symbols()









# ==========================
# TRADE HISTORY FROM MT5
# ==========================


@router.get("/history")
def trade_history(

    request: Request

):


    auth = check_auth(request)


    if auth:

        return auth



    history = MT5History()



    return history.get_history()







# ==========================
# IMPORT MT5 HISTORY TO DATABASE
# ==========================


@router.post("/import-history")
def import_history(

    request: Request

):


    auth = check_auth(request)


    if auth:

        return auth



    return import_mt5_history()