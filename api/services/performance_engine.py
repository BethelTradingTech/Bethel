"""
Bethel Trading Technologies
Unified Investor Performance Analytics Engine

Combines:
- EquitySnapshot analytics
- Trade performance analytics
- Risk metrics
"""

from __future__ import annotations


from typing import Dict, List


import math

import numpy as np


from api.database import SessionLocal

from api.models import EquitySnapshot

from api.services.trade_performance import (
    get_trade_performance
)

from api.config.investor import (
    INITIAL_INVESTMENT
)



# =====================================================
# CONFIGURATION
# =====================================================


STARTING_CAPITAL = INITIAL_INVESTMENT


TRADING_DAYS_PER_YEAR = 252





# =====================================================
# PERFORMANCE ENGINE
# =====================================================


class PerformanceEngine:


    def __init__(self):

        self.db = SessionLocal()



    # =================================================
    # TRADE METRICS
    # =================================================


    def trade_metrics(self) -> Dict:


        try:

            data = get_trade_performance()


            performance = data.get(

                "performance",

                {}

            )


            risk = data.get(

                "risk",

                {}

            )


            return {


                "total_trades":

                    performance.get(

                        "total_trades",

                        0

                    ),


                "win_rate":

                    performance.get(

                        "win_rate",

                        0

                    ),


                "profit_factor":

                    performance.get(

                        "profit_factor",

                        0

                    ),


                "sharpe_ratio":

                    risk.get(

                        "sharpe_ratio",

                        0

                    ),


                "sortino_ratio":

                    risk.get(

                        "sortino_ratio",

                        0

                    ),


                "max_drawdown":

                    risk.get(

                        "max_drawdown",

                        0

                    )

            }


        except Exception:


            return {


                "total_trades":0,

                "win_rate":0,

                "profit_factor":0,

                "sharpe_ratio":0,

                "sortino_ratio":0,

                "max_drawdown":0

            }


    # =================================================
    # LOAD EQUITY HISTORY
    # =================================================


    def load_history(self) -> List[EquitySnapshot]:


        return (

            self.db.query(

                EquitySnapshot

            )

            .order_by(

                EquitySnapshot.timestamp.asc()

            )

            .all()

        )





    # =================================================
    # EQUITY ARRAY
    # =================================================


    def equity_values(

        self,

        history: List[EquitySnapshot]

    ) -> np.ndarray:


        return np.array(

            [

                float(

                    item.equity

                )

                for item in history

            ],

            dtype=float

        )





    # =================================================
    # RETURN SERIES
    # =================================================


    def returns(

        self,

        equity: np.ndarray

    ) -> np.ndarray:


        if len(equity) < 2:

            return np.array([])



        return (

            np.diff(equity)

            /

            equity[:-1]

        )





    # =================================================
    # TOTAL RETURN
    # =================================================


    def total_return(

        self,

        current_equity: float

    ) -> float:


        return (

            (

                current_equity

                -

                STARTING_CAPITAL

            )

            /

            STARTING_CAPITAL

        ) * 100





    # =================================================
    # DAILY RETURN
    # =================================================


    def daily_return(

        self,

        returns

    ) -> float:


        if len(returns) == 0:

            return 0.0



        return round(

            float(

                np.mean(returns)

            )

            *

            100,

            4

        )





    # =================================================
    # MONTHLY RETURN
    # =================================================


    def monthly_return(

        self,

        returns

    ) -> float:


        if len(returns) == 0:

            return 0.0



        return round(

            (

                (

                    1 +

                    np.mean(returns)

                )

                ** 21

                -

                1

            )

            *

            100,

            2

        )





    # =================================================
    # VOLATILITY
    # =================================================


    def volatility(

        self,

        returns

    ) -> float:


        if len(returns) < 2:

            return 0.0



        return float(

            np.std(

                returns,

                ddof=1

            )

            *

            math.sqrt(

                TRADING_DAYS_PER_YEAR

            )

        )


    # =================================================
    # EQUITY MAX DRAW DOWN
    # =================================================


    def equity_drawdown(

        self,

        equity

    ) -> float:


        if len(equity) == 0:

            return 0.0



        peak = np.maximum.accumulate(

            equity

        )


        drawdown = (

            equity

            -

            peak

        ) / peak



        return abs(

            float(

                np.min(drawdown)

            )

        ) * 100





    # =================================================
    # SHARPE RATIO
    # Uses trade engine first
    # =================================================


    def sharpe_ratio(

        self,

        returns,

        trade_data

    ) -> float:


        value = trade_data.get(

            "sharpe_ratio",

            0

        )


        if value:

            return round(

                float(value),

                2

            )



        if len(returns) < 2:

            return 0.0



        deviation = np.std(

            returns,

            ddof=1

        )


        if deviation == 0:

            return 0.0



        result = (

            np.mean(returns)

            /

            deviation

        ) * math.sqrt(

            TRADING_DAYS_PER_YEAR

        )


        return round(

            float(result),

            2

        )





    # =================================================
    # SORTINO RATIO
    # =================================================


    def sortino_ratio(

        self,

        returns,

        trade_data

    ) -> float:


        value = trade_data.get(

            "sortino_ratio",

            0

        )


        if value:

            return round(

                float(value),

                2

            )



        if len(returns) < 2:

            return 0.0



        downside = returns[

            returns < 0

        ]



        if len(downside) == 0:

            return 0.0



        deviation = np.std(

            downside,

            ddof=1

        )


        if deviation == 0:

            return 0.0



        result = (

            np.mean(returns)

            /

            deviation

        ) * math.sqrt(

            TRADING_DAYS_PER_YEAR

        )


        return round(

            float(result),

            2

        )





    # =================================================
    # MAX DRAWDOWN AMOUNT
    # From trade engine
    # =================================================


    def maximum_drawdown_amount(

        self,

        trade_data

    ) -> float:


        return round(

            float(

                trade_data.get(

                    "max_drawdown",

                    0

                )

            ),

            2

        )





    # =================================================
    # RECOVERY FACTOR
    # =================================================


    def recovery_factor(

        self,

        current_equity,

        drawdown_amount

    ):


        profit = (

            current_equity

            -

            STARTING_CAPITAL

        )


        if drawdown_amount <= 0:

            return None



        return round(

            profit

            /

            drawdown_amount,

            2

        )


    # =================================================
    # CONSISTENCY SCORE
    # =================================================


    def consistency_score(

        self,

        returns,

        max_drawdown_percent,

        volatility

    ) -> float:


        if len(returns) == 0:

            return 0.0



        positive = (

            np.sum(

                returns > 0

            )

            /

            len(returns)

        ) * 100



        drawdown_score = max(

            0,

            100 -

            (

                max_drawdown_percent * 10

            )

        )



        volatility_score = max(

            0,

            100 -

            (

                volatility * 100

            )

        )



        score = (

            positive * 0.4

            +

            drawdown_score * 0.3

            +

            volatility_score * 0.3

        )



        return round(

            min(

                100,

                max(

                    0,

                    score

                )

            ),

            2

        )





    # =================================================
    # RISK LEVEL
    # =================================================


    def risk_level(

        self,

        drawdown_percent,

        volatility

    ) -> str:



        if (

            drawdown_percent < 5

            and

            volatility < 0.10

        ):

            return "LOW"





        if (

            drawdown_percent < 10

            and

            volatility < 0.20

        ):

            return "MEDIUM"





        return "HIGH"





    # =================================================
    # PERFORMANCE GRADE
    # =================================================


    def performance_grade(

        self,

        total_return,

        profit_factor,

        drawdown_percent

    ) -> str:



        if (

            total_return >= 20

            and

            profit_factor >= 3

            and

            drawdown_percent < 5

        ):

            return "A+"





        if (

            total_return >= 10

            and

            profit_factor >= 2

            and

            drawdown_percent < 10

        ):

            return "A"





        if (

            total_return > 0

            and

            profit_factor >= 1.5

        ):

            return "B"





        return "C"



    # =================================================
    # GENERATE INVESTOR ANALYTICS REPORT
    # =================================================


    def generate_report(

        self

    ) -> Dict:



        history = self.load_history()



        if not history:


            return {


                "status":

                "error",


                "message":

                "No equity history available"

            }





        # Equity calculations

        equity = self.equity_values(

            history

        )


        returns = self.returns(

            equity

        )



        current_equity = float(

            equity[-1]

        )



        total_return = self.total_return(

            current_equity

        )



        equity_drawdown = self.equity_drawdown(

            equity

        )



        volatility = self.volatility(

            returns

        )





        # Trade calculations

        trade_data = self.trade_metrics()



        profit_factor = round(

            float(

                trade_data.get(

                    "profit_factor",

                    0

                )

            ),

            2

        )



        drawdown_amount = self.maximum_drawdown_amount(

            trade_data

        )



        # Convert dollar drawdown to %

        drawdown_percent = 0


        if STARTING_CAPITAL > 0:


            drawdown_percent = (

                drawdown_amount

                /

                STARTING_CAPITAL

            ) * 100





        consistency = self.consistency_score(

            returns,

            drawdown_percent,

            volatility

        )



        recovery = self.recovery_factor(

            current_equity,

            drawdown_amount

        )





        return {


            "status":

            "success",



            "starting_capital":

            STARTING_CAPITAL,



            "current_equity":

            round(

                current_equity,

                2

            ),



            "total_return_percent":

            round(

                total_return,

                2

            ),



            "daily_return_percent":

            self.daily_return(

                returns

            ),



            "monthly_return_percent":

            self.monthly_return(

                returns

            ),



            "volatility":

            round(

                volatility * 100,

                2

            ),



            "maximum_drawdown_amount":

            drawdown_amount,



            "maximum_drawdown_percent":

            round(

                drawdown_percent,

                2

            ),



            "profit_factor":

            profit_factor,



            "sharpe_ratio":

            self.sharpe_ratio(

                returns,

                trade_data

            ),



            "sortino_ratio":

            self.sortino_ratio(

                returns,

                trade_data

            ),



            "recovery_factor":

            recovery,



            "consistency_score":

            consistency,



            "risk_level":

            self.risk_level(

                drawdown_percent,

                volatility

            ),



            "performance_grade":

            self.performance_grade(

                total_return,

                profit_factor,

                drawdown_percent

            ),



            "total_trades":

            trade_data.get(

                "total_trades",

                0

            ),



            "win_rate":

            trade_data.get(

                "win_rate",

                0

            ),



            "snapshots_analyzed":

            len(history)

        }





    # =================================================
    # CLOSE DATABASE
    # =================================================


    def close(

        self

    ):


        if self.db:

            self.db.close()





# =====================================================
# API ACCESS FUNCTION
# =====================================================


def get_performance_analytics() -> Dict:


    engine = PerformanceEngine()



    try:


        return engine.generate_report()



    finally:


        engine.close()