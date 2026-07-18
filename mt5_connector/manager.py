"""
Bethel Trading Technologies
MT5 Connection Recovery Manager
"""

import MetaTrader5 as mt5


class MT5Manager:


    @classmethod
    def ensure_connection(cls):

        # Check existing MT5 connection
        account = mt5.account_info()

        if account is not None:
            return True


        # Start MT5 terminal
        initialized = mt5.initialize(
            path=r"C:\Program Files\MetaTrader 5\terminal64.exe"
        )


        if not initialized:
            return False


        # Check account after initialization
        account = mt5.account_info()


        if account is not None:
            return True


        return False