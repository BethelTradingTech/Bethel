"""
Bethel Trading Technologies
Daily Performance Engine

Converts equity snapshots into daily
investor performance data.
"""


from collections import defaultdict

import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot



class DailyPerformanceEngine:


    def __init__(self):

        self.db = SessionLocal()



    # =====================================
    # LOAD SNAPSHOTS
    # =====================================

    def load_snapshots(self):

        return (

            self.db.query(

                EquitySnapshot

            )

            .order_by(

                EquitySnapshot.timestamp.asc()

            )

            .all()

        )



    # =====================================
    # BUILD DAILY EQUITY CURVE
    # =====================================

    def daily_equity_curve(self):


        snapshots = self.load_snapshots()


        if not snapshots:

            return []



        daily = defaultdict(list)



        for item in snapshots:


            day = item.timestamp.date()


            daily[day].append(

                float(item.equity)

            )



        curve = []



        for day, values in sorted(daily.items()):


            curve.append({

                "date": str(day),

                "equity": values[-1]

            })



        return curve

    # =====================================
    # CALCULATE DAILY RETURNS
    # =====================================

    def daily_returns(self):


        curve = self.daily_equity_curve()


        if len(curve) < 2:

            return []



        returns = []



        for i in range(1, len(curve)):


            previous = curve[i-1]["equity"]

            current = curve[i]["equity"]



            if previous == 0:

                continue



            change = (

                current - previous

            ) / previous



            returns.append({

                "date":

                curve[i]["date"],


                "return":

                float(change)

            })



        return returns

    # =====================================
    # DAILY RISK METRICS
    # =====================================

    def risk_metrics(self):


        daily = self.daily_returns()


        if len(daily) < 2:

            return {

                "volatility": 0.0,

                "sharpe_ratio": 0.0,

                "sortino_ratio": 0.0

            }



        returns = np.array(

            [

                item["return"]

                for item in daily

            ]

        )



        volatility = (

            np.std(

                returns,

                ddof=1

            )

            *

            np.sqrt(252)

        )



        sharpe = 0.0


        if np.std(returns) != 0:

            sharpe = (

                np.mean(returns)

                /

                np.std(returns)

            ) * np.sqrt(252)



        downside = returns[returns < 0]



        sortino = 0.0


        if len(downside) > 0:


            downside_std = np.std(

                downside,

                ddof=1

            )


            if downside_std != 0:


                sortino = (

                    np.mean(returns)

                    /

                    downside_std

                ) * np.sqrt(252)



        return {

            "volatility":

            round(float(volatility),4),


            "sharpe_ratio":

            round(float(sharpe),2),


            "sortino_ratio":

            round(float(sortino),2)

        }

    # =====================================
    # DAILY PERFORMANCE REPORT
    # =====================================

    def report(self):


        curve = self.daily_equity_curve()

        metrics = self.risk_metrics()


        return {


            "status":

            "success",


            "days_analyzed":

            len(curve),


            "daily_equity_curve":

            curve,


            "risk_metrics":

            metrics

        }



# =====================================
# HELPER FUNCTION
# =====================================

def get_daily_performance():

    engine = DailyPerformanceEngine()

    try:

        return engine.report()

    finally:

        engine.db.close()
