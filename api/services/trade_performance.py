"""
Bethel Trading Technologies
Trade Performance Analytics Engine
"""

import numpy as np

from api.database import SessionLocal
from api.models import Trade



class TradePerformanceEngine:


    def __init__(self):

        self.db = SessionLocal()



    # ==============================
    # LOAD CLOSED TRADES
    # ==============================

    def load_trades(self):

        return (

            self.db.query(Trade)

            .filter(
                Trade.status == "CLOSED"
            )

            .order_by(
                Trade.closed_at.asc()
            )

            .all()

        )



    # ==============================
    # PROFIT SERIES
    # ==============================

    def profits(self):

        trades = self.load_trades()

        return np.array(

            [
                float(t.profit)

                for t in trades
            ],

            dtype=float

        )



    # ==============================
    # PERFORMANCE STATISTICS
    # ==============================

    def statistics(self):

        profits = self.profits()


        if len(profits) == 0:

            return {

                "total_trades":0,

                "winning_trades":0,

                "losing_trades":0,

                "win_rate":0,

                "gross_profit":0,

                "gross_loss":0,

                "profit_factor":0,

                "average_win":0,

                "average_loss":0,

                "expectancy":0

            }



        wins = profits[profits > 0]

        losses = profits[profits < 0]



        total = len(profits)

        winners = len(wins)

        losers = len(losses)



        win_rate = (

            winners / total

        ) * 100



        gross_profit = float(wins.sum())

        gross_loss = abs(float(losses.sum()))



        profit_factor = (

            gross_profit / gross_loss

            if gross_loss > 0

            else 0

        )



        average_win = (

            float(wins.mean())

            if winners > 0

            else 0

        )



        average_loss = (

            float(losses.mean())

            if losers > 0

            else 0

        )



        expectancy = (

            (

                win_rate/100 * average_win

            )

            +

            (

                (losers/total)

                *

                average_loss

            )

        )



        return {


            "total_trades":

            total,


            "winning_trades":

            winners,


            "losing_trades":

            losers,


            "win_rate":

            round(win_rate,2),


            "gross_profit":

            round(gross_profit,2),


            "gross_loss":

            round(gross_loss,2),


            "profit_factor":

            round(profit_factor,2),


            "average_win":

            round(average_win,2),


            "average_loss":

            round(average_loss,2),


            "expectancy":

            round(expectancy,2)

        }



    # ==============================
    # RISK METRICS
    # ==============================

    def risk_metrics(self):

        profits = self.profits()



        if len(profits)<2:

            return {

                "sharpe_ratio":0,

                "sortino_ratio":0,

                "max_drawdown":0

            }



        returns = profits / 100000



        mean = np.mean(returns)

        std = np.std(returns)



        sharpe = (

            mean/std

            if std !=0

            else 0

        )



        downside = returns[returns<0]



        sortino = (

            mean / np.std(downside)

            if len(downside)>1

            and np.std(downside)!=0

            else 0

        )



        equity = np.cumsum(profits)


        peak = np.maximum.accumulate(equity)


        drawdown = equity - peak


        max_drawdown = abs(drawdown.min())



        return {


            "sharpe_ratio":

            round(float(sharpe),2),


            "sortino_ratio":

            round(float(sortino),2),


            "max_drawdown":

            round(float(max_drawdown),2)

        }



    # ==============================
    # COMPLETE REPORT
    # ==============================

    def report(self):

        return {


            "status":

            "success",


            "performance":

            self.statistics(),


            "risk":

            self.risk_metrics()

        }



def get_trade_performance():

    engine = TradePerformanceEngine()


    try:

        return engine.report()


    finally:

        engine.db.close()