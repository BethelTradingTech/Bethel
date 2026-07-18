"""
Bethel Trading Technologies
Portfolio Simulator
"""


class Portfolio:


    def __init__(
        self,
        starting_balance=100000
    ):

        self.balance = starting_balance

        self.equity = starting_balance

        self.trades = []



    def add_trade(
        self,
        trade
    ):

        self.trades.append(
            trade
        )



    def update_balance(
        self,
        profit
    ):

        self.balance += profit

        self.equity = self.balance



    def get_summary(self):

        return {

            "balance": self.balance,

            "equity": self.equity,

            "total_trades": len(self.trades)

        }