"""
Bethel Trading Technologies
MT5 Positions Data Module
"""

import MetaTrader5 as mt5

from mt5_connector.manager import MT5Manager



class MT5Positions:


    def get_positions(self):


        connected = MT5Manager.ensure_connection()


        if not connected:

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        positions = mt5.positions_get()



        if positions is None:

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        data = []



        for position in positions:


            data.append({

                "ticket": position.ticket,

                "symbol": position.symbol,

                "type": position.type,

                "volume": position.volume,

                "price_open": position.price_open,

                "price_current": position.price_current,

                "profit": position.profit,

                "sl": position.sl,

                "tp": position.tp

            })



        return {

            "status": "success",

            "count": len(data),

            "positions": data

        }