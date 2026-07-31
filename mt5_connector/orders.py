"""MT5 order adapter with global switch and target-account verification."""

import MetaTrader5 as mt5

from config.execution import EXECUTION_MODE, LIVE_COPY_ENABLED


class MT5Order:
    def __init__(self, *, target_login: str, target_server: str):
        self.target_login = str(target_login).strip()
        self.target_server = str(target_server).strip()

    def _verify_target_account(self):
        if EXECUTION_MODE != "LIVE" or not LIVE_COPY_ENABLED:
            return {
                "status": "disabled",
                "message": "Global live-copy emergency switch is off",
            }

        if not mt5.initialize():
            return {"status": "failed", "message": str(mt5.last_error())}

        account = mt5.account_info()
        if account is None:
            return {"status": "failed", "message": "Unable to read MT5 account"}

        actual_login = str(account.login)
        actual_server = str(getattr(account, "server", "") or "")
        if actual_login != self.target_login:
            return {
                "status": "failed",
                "message": "Connected MT5 terminal does not match subscriber account",
            }
        if (
            actual_server
            and self.target_server
            and actual_server.casefold() != self.target_server.casefold()
        ):
            return {
                "status": "failed",
                "message": "Connected MT5 terminal does not match subscriber server",
            }
        if not bool(getattr(account, "trade_allowed", False)):
            return {
                "status": "failed",
                "message": "Trading is not allowed on the connected MT5 account",
            }
        return None

    def send_order(
        self,
        symbol,
        side,
        volume,
        stop_loss=None,
        take_profit=None,
    ):
        verification_error = self._verify_target_account()
        if verification_error:
            return verification_error

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"status": "failed", "message": f"Symbol {symbol} not found"}
        if not symbol_info.visible and not mt5.symbol_select(symbol, True):
            return {"status": "failed", "message": f"Unable to select {symbol}"}

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"status": "failed", "message": "No market tick available"}

        side = str(side).upper()
        if side == "BUY":
            order_type, price = mt5.ORDER_TYPE_BUY, tick.ask
        elif side == "SELL":
            order_type, price = mt5.ORDER_TYPE_SELL, tick.bid
        else:
            return {"status": "failed", "message": "Side must be BUY or SELL"}

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 260717,
            "comment": "Bethel Trading Technologies",
        }
        if stop_loss is not None:
            request["sl"] = float(stop_loss)
        if take_profit is not None:
            request["tp"] = float(take_profit)

        result = mt5.order_send(request)
        if result is None:
            return {"status": "failed", "message": str(mt5.last_error())}
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "status": "failed",
                "retcode": result.retcode,
                "message": result.comment,
            }
        return {
            "status": "success",
            "ticket": result.order,
            "symbol": symbol,
            "side": side,
            "volume": float(volume),
            "price": price,
            "account": self.target_login,
            "server": self.target_server,
        }
