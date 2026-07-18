"""
Bethel Trading Technologies
Order Management Engine

Paper execution layer.
"""


import datetime


class OrderManager:


    def __init__(self):

        self.orders = []



    def open_trade(
        self,
        symbol,
        side,
        size,
        stop_loss,
        take_profit
    ):


        order = {

            "symbol": symbol,

            "side": side,

            "size": size,

            "stop_loss": stop_loss,

            "take_profit": take_profit,

            "time": datetime.datetime.now()

        }


        self.orders.append(order)


        print("==============================")
        print("TRADE OPENED")
        print("==============================")

        print(order)


        return order