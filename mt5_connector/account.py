"""
Bethel Trading Technologies
MT5 Account Data Module
"""

import MetaTrader5 as mt5

from mt5_connector.manager import MT5Manager



class MT5Account:


    def get_account_info(self):


        connected = MT5Manager.ensure_connection()


        if not connected:

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        account = mt5.account_info()



        if account is None:

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        return {


            "status": "connected",


            "login": account.login,


            "name": account.name,


            "server": account.server,


            "currency": account.currency,


            "balance": account.balance,


            "equity": account.equity,


            "profit": account.profit,


            "margin": account.margin,


            "margin_free": account.margin_free,


            "margin_level": account.margin_level,


            "leverage": account.leverage

        }