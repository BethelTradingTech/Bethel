"""
Bethel Trading Technologies
Persistent MT5 Connection Manager
"""

import MetaTrader5 as mt5


class MT5Connection:

    def __init__(
        self,
        account_number,
        server,
        password
    ):

        self.account_number = int(account_number)
        self.server = server
        self.password = password
        self.connected = False


    def initialize(self):

        """
        Start MT5 terminal connection
        """

        # Check existing MT5 connection
        if mt5.terminal_info() is not None:
            return True


        initialized = mt5.initialize(
            path=r"C:\Program Files\MetaTrader 5\terminal64.exe"
        )


        if not initialized:

            self.connected = False

            return False


        return True



    def connect(self):

        """
        Main connection method used by API
        """

        if not self.initialize():

            return {
                "status": "failed",
                "message": str(mt5.last_error())
            }


        return self.login()



    def login(self):

        """
        Login to MT5 trading account
        """

        authorized = mt5.login(
            self.account_number,
            password=self.password,
            server=self.server
        )


        if not authorized:

            self.connected = False

            return {
                "status": "failed",
                "message": str(mt5.last_error())
            }


        self.connected = True

        return self.account_info()



    def account_info(self):

        """
        Get live account information
        """

        if not self.connected:

            return {
                "status": "failed",
                "message": "MT5 not connected"
            }


        account = mt5.account_info()


        if account is None:

            self.connected = False

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



    def positions(self):

        """
        Get open positions
        """

        if not self.connected:

            connection = self.connect()

            if connection.get("status") == "failed":

                return connection



        positions = mt5.positions_get()


        if positions is None:

            return {

                "status": "failed",

                "message": str(mt5.last_error())

            }



        data = []


        for p in positions:

            data.append({

                "ticket": p.ticket,

                "symbol": p.symbol,

                "type": p.type,

                "volume": p.volume,

                "price_open": p.price_open,

                "price_current": p.price_current,

                "profit": p.profit,

                "sl": p.sl,

                "tp": p.tp

            })



        return {

            "status": "success",

            "count": len(data),

            "positions": data

        }



    def shutdown(self):

        """
        Close MT5 terminal connection
        """

        mt5.shutdown()

        self.connected = False