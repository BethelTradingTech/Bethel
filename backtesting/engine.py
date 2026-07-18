"""
Bethel Trading Technologies
Backtesting Engine

AuraStyle TrendHunter Simulation
"""


from strategies.trend_hunter import TrendHunter
from backtesting.portfolio import Portfolio
from backtesting.trade_manager import TradeManager



class BacktestEngine:


    def __init__(
        self,
        starting_balance=100000
    ):

        self.portfolio = Portfolio(
            starting_balance
        )

        self.trade_manager = TradeManager(
            starting_balance
        )

        self.strategy = TrendHunter()


        # Risk settings

        self.take_profit = 0.02      # 2%
        self.stop_loss = 0.02        # 2%

        self.max_open_trades = 5



    def run(
        self,
        data,
        symbol
    ):


        print("==============================")
        print("BETHEL BACKTEST ENGINE")
        print("==============================")


        open_trades = []



        for i in range(200, len(data)):


            current_price = float(
                data.iloc[i]["close"]
            )



            # ==============================
            # MANAGE OPEN TRADES
            # ==============================

            for trade in open_trades[:]:


                entry = trade["entry"]



                # BUY MANAGEMENT

                if trade["direction"] == "BUY":


                    if current_price >= entry * (1 + self.take_profit):

                        self.trade_manager.close_trade(
                            trade,
                            current_price
                        )

                        open_trades.remove(trade)



                    elif current_price <= entry * (1 - self.stop_loss):

                        self.trade_manager.close_trade(
                            trade,
                            current_price
                        )

                        open_trades.remove(trade)



                # SELL MANAGEMENT

                elif trade["direction"] == "SELL":


                    if current_price <= entry * (1 - self.take_profit):

                        self.trade_manager.close_trade(
                            trade,
                            current_price
                        )

                        open_trades.remove(trade)



                    elif current_price >= entry * (1 + self.stop_loss):

                        self.trade_manager.close_trade(
                            trade,
                            current_price
                        )

                        open_trades.remove(trade)




            # ==============================
            # GENERATE NEW SIGNAL
            # ==============================


            candle_data = data.iloc[:i]


            signal = self.strategy.analyze(
                candle_data
            )


            direction = signal["signal"]



            # ==============================
            # OPEN NEW TRADE
            # ==============================


            if (
                direction != "HOLD"
                and len(open_trades) < self.max_open_trades
            ):


                trade = self.trade_manager.open_trade(
                    symbol,
                    direction,
                    current_price,
                    1
                )


                open_trades.append(
                    trade
                )


                print(
                    "OPEN:",
                    trade
                )



        # ==============================
        # CLOSE REMAINING POSITIONS
        # ==============================


        final_price = float(
            data.iloc[-1]["close"]
        )


        for trade in self.trade_manager.trades:


            if trade["status"] == "OPEN":


                self.trade_manager.close_trade(
                    trade,
                    final_price
                )



        # ==============================
        # RESULTS
        # ==============================


        closed = self.trade_manager.get_closed_trades()



        print("==============================")
        print("BACKTEST COMPLETE")
        print("==============================")


        print(
            "Closed Trades:",
            len(closed)
        )


        print(
            "Final Balance:",
            round(self.trade_manager.balance,2)
        )


        print("==============================")


        return self.trade_manager