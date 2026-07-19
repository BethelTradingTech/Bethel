"""
Bethel Trading Technologies
Daily Performance Engine
"""

import numpy as np

from api.database import SessionLocal

from api.models import EquitySnapshot



class DailyPerformanceEngine:


    def __init__(self):

        self.db = SessionLocal()



    # ==============================
    # EQUITY HISTORY
    # ==============================

    def equity_history(self):


        records = (

            self.db.query(EquitySnapshot)

            .order_by(
                EquitySnapshot.timestamp.asc()
            )

            .all()

        )


        return [

            {

            "date":
            r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),

            "equity":
            r.equity

            }

            for r in records

        ]




    # ==============================
    # RETURNS
    # ==============================

    def returns(self):


        history = self.equity_history()


        equities = [

            x["equity"]

            for x in history

        ]



        if len(equities) < 2:

            return []



        returns = []



        for i in range(1,len(equities)):


            previous = equities[i-1]

            current = equities[i]



            if previous != 0:


                returns.append(

                    (

                    current - previous

                    )

                    /

                    previous

                )



        return returns





    # ==============================
    # RISK METRICS
    # ==============================

    def risk_metrics(self):


        returns = self.returns()



        if len(returns) < 2:


            return {

            "volatility":0,

            "sharpe_ratio":0,

            "sortino_ratio":0

            }



        data = np.array(
            returns
        )



        volatility = np.std(data)



        mean_return = np.mean(data)



        sharpe = (

            mean_return /

            volatility

        ) if volatility !=0 else 0




        negative = data[data < 0]



        downside = (

            np.std(negative)

            if len(negative)

            else 0

        )



        sortino = (

            mean_return /

            downside

        ) if downside !=0 else 0




        return {


        "volatility":

        round(float(volatility*100),4),



        "sharpe_ratio":

        round(float(sharpe),4),



        "sortino_ratio":

        round(float(sortino),4)


        }






def get_daily_performance():


    engine = DailyPerformanceEngine()


    try:


        return {


        "status":

        "success",


        "snapshots":

        len(
        engine.equity_history()
        ),


        "risk_metrics":

        engine.risk_metrics()


        }


    finally:


        engine.db.close()