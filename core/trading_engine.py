"""
Bethel Trading Technologies
Master Trading Engine

Connects Strategy + Risk + Execution
"""


from strategies.trend_hunter import TrendHunter

from risk.risk_manager import RiskManager

from execution.order_manager import OrderManager

from execution.position_manager import PositionManager

from execution.stop_manager import calculate_levels



class TradingEngine:


    def __init__(self):

        self.strategy = TrendHunter()

        self.risk = RiskManager()

        self.orders = OrderManager()

        self.positions = PositionManager()



    def run_cycle(
        self,
        market_data,
        symbol,
        balance,
        equity
    ):


        print("==============================")
        print("BETHEL TRADING ENGINE")
        print("==============================")


        # 1. Analyze market

        signal = self.strategy.analyze(
            market_data
        )


        print("Strategy Signal:")
        print(signal)



        direction = signal["signal"]



        # 2. Risk approval

        decision = self.risk.evaluate_trade(

            signal=direction,

            balance=balance,

            equity=equity,

            stop_loss_distance=500

        )


        print("Risk Decision:")
        print(decision)



        if decision["approved"] == False:

            print("Trade rejected")

            return None



        # 3. Calculate SL / TP

        entry_price = market_data.iloc[-1]["close"]


        levels = calculate_levels(

            entry_price,

            atr=100,

            direction=direction

        )



        # 4. Execute paper trade

        trade = self.orders.open_trade(

            symbol=symbol,

            side=direction,

            size=decision["position_size"],

            stop_loss=levels["stop_loss"],

            take_profit=levels["take_profit"]

        )


        # 5. Store position

        self.positions.add_position(
            trade
        )


        return trade