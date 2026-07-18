class TradeManager:

    def __init__(self, balance=100000):
        self.starting_balance = balance
        self.balance = balance
        self.equity = balance
        self.trades = []


    def open_trade(self, symbol, direction, entry, size=1):

        trade = {

            "symbol": symbol,
            "direction": direction,
            "entry": float(entry),
            "size": size,
            "status": "OPEN"

        }

        self.trades.append(trade)

        return trade



    def close_trade(self, trade, exit_price):

        if trade["direction"] == "BUY":

            pnl = (exit_price - trade["entry"]) * trade["size"]

        else:

            pnl = (trade["entry"] - exit_price) * trade["size"]


        trade["exit"] = float(exit_price)
        trade["pnl"] = round(pnl, 2)
        trade["status"] = "CLOSED"


        self.balance += pnl
        self.equity = self.balance


        return trade



    def get_closed_trades(self):

        return [
            t for t in self.trades
            if t["status"] == "CLOSED"
        ]



    def get_open_trades(self):

        return [
            t for t in self.trades
            if t["status"] == "OPEN"
        ]



    def get_summary(self):

        closed = self.get_closed_trades()
        opened = self.get_open_trades()

        return {

            "starting_balance": self.starting_balance,

            "ending_balance": round(self.balance, 2),

            "profit": round(
                self.balance - self.starting_balance,
                2
            ),

            "return_percent": round(
                ((self.balance - self.starting_balance)
                / self.starting_balance) * 100,
                2
            ),

            "closed_trades": len(closed),

            "open_trades": len(opened)

        }