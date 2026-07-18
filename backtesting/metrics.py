class PerformanceMetrics:

    def __init__(self, trades, starting_balance=100000):
        self.trades = trades
        self.starting_balance = starting_balance


    def calculate(self):

        balance = self.starting_balance
        wins = 0
        losses = 0
        total_profit = 0
        total_loss = 0


        for trade in self.trades:

            pnl = trade.get("pnl",0)

            balance += pnl

            if pnl > 0:
                wins += 1
                total_profit += pnl

            elif pnl < 0:
                losses += 1
                total_loss += abs(pnl)


        total_trades = len(self.trades)

        win_rate = 0
        if total_trades > 0:
            win_rate = (wins / total_trades) * 100


        profit_factor = 0
        if total_loss > 0:
            profit_factor = total_profit / total_loss


        return {

            "starting_balance": self.starting_balance,
            "ending_balance": round(balance,2),
            "return_percent": round(
                ((balance-self.starting_balance)
                /self.starting_balance)*100,2
            ),

            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate,2),
            "profit_factor": round(profit_factor,2)

        }