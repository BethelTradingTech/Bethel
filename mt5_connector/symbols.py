"""
Bethel Trading Technologies
MT5 Symbol Scanner
"""

import MetaTrader5 as mt5


class MT5Symbols:


    def get_symbols(self):

        if not mt5.initialize():

            return {
                "status": "failed",
                "message": str(mt5.last_error())
            }


        symbols = mt5.symbols_get()


        if symbols is None:

            return {
                "status": "failed",
                "message": str(mt5.last_error())
            }


        result = []


        for symbol in symbols:

            result.append(symbol.name)


        return {

            "status": "success",

            "count": len(result),

            "symbols": result[:200]

        }