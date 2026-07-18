"""
Bethel Trading Technologies
MT5 Trade History Collector
"""

import MetaTrader5 as mt5

from datetime import datetime, timedelta

from mt5_connector.manager import MT5Manager



class MT5History:


    def get_history(self, days=30):


        # Ensure MT5 connection
        connected = MT5Manager.ensure_connection()


        if not connected:

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        date_to = datetime.now()


        date_from = date_to - timedelta(
            days=days
        )



        deals = mt5.history_deals_get(
            date_from,
            date_to
        )



        if deals is None:

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        result = []



        for deal in deals:


            result.append({

                "ticket": deal.ticket,

                "symbol": deal.symbol,

                "type": deal.type,

                "volume": deal.volume,

                "price": deal.price,

                "profit": deal.profit,

                "commission": deal.commission,

                "swap": deal.swap,

                "time": datetime.fromtimestamp(
                    deal.time
                ).isoformat()

            })



        return {


            "status": "success",

            "count": len(result),

            "history": result

        }