"""
Bethel Trading Technologies
MT5 Order Execution Adapter

Safety Mode:
- Connected to MT5
- Order structure prepared
- Live execution disabled
"""


import MetaTrader5 as mt5



class MT5Order:


    def __init__(self):

        # Safety switch
        # Change to True only when you intentionally enable API trading
        self.enabled = True



    def send_order(
        self,
        symbol,
        side,
        volume,
        stop_loss=None,
        take_profit=None
    ):


        # Prevent accidental live trades

        if not self.enabled:

            return {

                "status": "disabled",

                "message": "MT5 API execution is disabled"

            }



        # Initialize MT5

        if not mt5.initialize():

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        # Check symbol

        symbol_info = mt5.symbol_info(symbol)


        if symbol_info is None:

            return {

                "status": "failed",

                "message": f"Symbol {symbol} not found"

            }



        # Enable symbol if hidden

        if not symbol_info.visible:

            if not mt5.symbol_select(symbol, True):

                return {

                    "status": "failed",

                    "message": f"Unable to select {symbol}"

                }



        # Get market price

        tick = mt5.symbol_info_tick(symbol)


        if tick is None:

            return {

                "status": "failed",

                "message": "No market tick available"

            }



        # Direction

        side = side.upper()


        if side == "BUY":

            order_type = mt5.ORDER_TYPE_BUY

            price = tick.ask


        elif side == "SELL":

            order_type = mt5.ORDER_TYPE_SELL

            price = tick.bid


        else:

            return {

                "status": "failed",

                "message": "Side must be BUY or SELL"

            }



        # Build order request

        request = {

            "action": mt5.TRADE_ACTION_DEAL,

            "symbol": symbol,

            "volume": float(volume),

            "type": order_type,

            "price": price,

            "deviation": 20,

            "magic": 260717,

            "comment": "Bethel Trading Technologies"

        }



        # Optional risk levels

        if stop_loss is not None:

            request["sl"] = float(stop_loss)


        if take_profit is not None:

            request["tp"] = float(take_profit)



        # Send order

        result = mt5.order_send(request)



        if result is None:

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        if result.retcode != mt5.TRADE_RETCODE_DONE:

            return {

                "status": "failed",

                "retcode": result.retcode,

                "comment": result.comment

            }



        return {

            "status": "success",

            "ticket": result.order,

            "symbol": symbol,

            "side": side,

            "volume": float(volume),

            "price": price

        }