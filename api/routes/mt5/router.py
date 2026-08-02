"""Read-only MT5 monitoring routes.

Bethel never accepts broker passwords and never submits orders. Authorized EAs
inside MetaTrader terminals own all execution.
"""

from fastapi import APIRouter, Depends

from api.auth.dependency import require_admin
from api.services.trade_importer import import_mt5_history
from mt5_connector.account import MT5Account
from mt5_connector.history import MT5History
from mt5_connector.positions import MT5Positions
from mt5_connector.symbols import MT5Symbols


router = APIRouter(prefix="/mt5", tags=["MT5 Monitoring"])


@router.get("/account")
def account_info(_admin=Depends(require_admin)):
    return MT5Account().get_account_info()


@router.get("/positions")
def open_positions(_admin=Depends(require_admin)):
    return MT5Positions().get_positions()


@router.get("/symbols")
def get_symbols(_admin=Depends(require_admin)):
    return MT5Symbols().get_symbols()


@router.get("/history")
def trade_history(_admin=Depends(require_admin)):
    return MT5History().get_history()


@router.post("/import-history")
def import_history(_admin=Depends(require_admin)):
    return import_mt5_history()
