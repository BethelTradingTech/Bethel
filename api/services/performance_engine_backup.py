"""
Bethel Trading Technologies
Performance Analytics Engine

Calculates investor performance statistics from
EquitySnapshot history.
"""

from __future__ import annotations

from typing import Dict, List

import math
import numpy as np

from api.database import SessionLocal
from api.models import EquitySnapshot
from api.config.investor import INITIAL_INVESTMENT


# =====================================================
# CONFIGURATION
# =====================================================

STARTING_CAPITAL = INITIAL_INVESTMENT

TRADING_DAYS_PER_YEAR = 252

RISK_FREE_RATE = 0.0


# =====================================================
# PERFORMANCE ENGINE
# =====================================================

class PerformanceEngine:

    def __init__(self):

        self.db = SessionLocal()

    # -----------------------------------------------

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

    # -----------------------------------------------

    def equity_values(

        self,

        history: List[EquitySnapshot]

    ) -> np.ndarray:

        if not history:

            return np.array([])

        return np.array(

            [

                float(item.equity)

                for item in history

            ],

            dtype=float

        )

    # -----------------------------------------------

    def balance_values(

        self,

        history: List[EquitySnapshot]

    ) -> np.ndarray:

        if not history:

            return np.array([])

        return np.array(

            [

                float(item.balance)

                for item in history

            ],

            dtype=float

        )

    # -----------------------------------------------

    def returns(

        self,

        equity: np.ndarray

    ) -> np.ndarray:

        if len(equity) < 2:

            return np.array([])

        return np.diff(

            equity

        ) / equity[:-1]


    # -----------------------------------------------
    # TOTAL RETURN
    # -----------------------------------------------

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



    # -----------------------------------------------
    # DAILY RETURN
    # -----------------------------------------------

    def daily_return(

        self,

        returns: np.ndarray

    ) -> float:

        if len(returns) == 0:

            return 0.0

        return float(

            np.mean(returns)

        ) * 100



    # -----------------------------------------------
    # MONTHLY RETURN
    # -----------------------------------------------

    def monthly_return(

        self,

        returns: np.ndarray

    ) -> float:

        if len(returns) == 0:

            return 0.0

        monthly = (

            1 + np.mean(returns)

        ) ** 21 - 1

        return float(

            monthly

        ) * 100



    # -----------------------------------------------
    # VOLATILITY
    # -----------------------------------------------

    def volatility(

        self,

        returns: np.ndarray

    ) -> float:

        if len(returns) < 2:

            return 0.0

        volatility = (

            np.std(

                returns,

                ddof=1

            )

            *

            math.sqrt(

                TRADING_DAYS_PER_YEAR

            )

        )

        return float(

            volatility

        )



    # -----------------------------------------------
    # MAXIMUM DRAWDOWN
    # -----------------------------------------------

    def max_drawdown(

        self,

        equity: np.ndarray

    ) -> float:

        if len(equity) == 0:

            return 0.0

        peak = np.maximum.accumulate(

            equity

        )

        drawdown = (

            equity - peak

        ) / peak

        return abs(

            float(

                np.min(drawdown)

            )

        ) * 100


    # -----------------------------------------------
    # SHARPE RATIO
    # -----------------------------------------------

    def sharpe_ratio(

        self,

        returns: np.ndarray

    ) -> float:

        if len(returns) < 2:

            return 0.0

        std = np.std(

            returns,

            ddof=1

        )

        if std == 0:

            return 0.0

        excess_return = np.mean(

            returns

        ) - (

            RISK_FREE_RATE / TRADING_DAYS_PER_YEAR

        )

        sharpe = (

            excess_return / std

        ) * math.sqrt(

            TRADING_DAYS_PER_YEAR

        )

        return round(

            float(sharpe),

            2

        )


    # -----------------------------------------------
    # SORTINO RATIO
    # -----------------------------------------------

    def sortino_ratio(

        self,

        returns: np.ndarray

    ) -> float:

        if len(returns) < 2:

            return 0.0

        downside = returns[returns < 0]

        if len(downside) == 0:

            return 0.0

        downside_std = np.std(

            downside,

            ddof=1

        )

        if downside_std == 0:

            return 0.0

        excess_return = np.mean(

            returns

        ) - (

            RISK_FREE_RATE / TRADING_DAYS_PER_YEAR

        )

        sortino = (

            excess_return / downside_std

        ) * math.sqrt(

            TRADING_DAYS_PER_YEAR

        )

        return round(

            float(sortino),

            2

        )


    # -----------------------------------------------
    # RECOVERY FACTOR
    # -----------------------------------------------

    def recovery_factor(

        self,

        current_equity: float,

        max_drawdown: float

    ):

        net_profit = (

            current_equity

            -

            STARTING_CAPITAL

        )

        if max_drawdown <= 0:

            return None

        drawdown_amount = (

            STARTING_CAPITAL

            *

            max_drawdown

            / 100

        )

        if drawdown_amount == 0:

            return None

        recovery = (

            net_profit

            /

            drawdown_amount

        )

        return round(

            float(recovery),

            2

        )


    # -----------------------------------------------
    # CONSISTENCY SCORE
    # -----------------------------------------------

    def consistency_score(

        self,

        returns: np.ndarray,

        max_drawdown: float,

        volatility: float

    ) -> float:

        if len(returns) == 0:

            return 0.0

        # Percentage of positive periods
        positive_periods = (

            np.sum(returns > 0)

            /

            len(returns)

        ) * 100


        # Drawdown component (0–100)
        drawdown_score = max(

            0,

            100 - (max_drawdown * 10)

        )


        # Volatility component (0–100)
        volatility_score = max(

            0,

            100 - (volatility * 100)

        )


        # Weighted score
        score = (

            positive_periods * 0.40 +

            drawdown_score * 0.30 +

            volatility_score * 0.30

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


    # -----------------------------------------------
    # RISK LEVEL
    # -----------------------------------------------

    def risk_level(

        self,

        max_drawdown: float,

        volatility: float

    ) -> str:

        if max_drawdown < 5 and volatility < 0.10:

            return "LOW"

        if max_drawdown < 10 and volatility < 0.20:

            return "MEDIUM"

        return "HIGH"


    # -----------------------------------------------
    # PERFORMANCE GRADE
    # -----------------------------------------------

    def performance_grade(

        self,

        consistency: float

    ) -> str:

        if consistency >= 90:

            return "A+"

        if consistency >= 80:

            return "A"

        if consistency >= 70:

            return "B"

        if consistency >= 60:

            return "C"

        return "D"

    # -----------------------------------------------
    # COMPLETE ANALYTICS REPORT
    # -----------------------------------------------

    def generate_report(self) -> Dict:


        try:

            history = self.load_history()


            if not history:

                return {

                    "status": "error",

                    "message": "No equity history available"

                }



            equity = self.equity_values(

                history

            )


            returns = self.returns(

                equity

            )



            current_equity = float(

                equity[-1]

            )



            max_dd = self.max_drawdown(

                equity

            )



            vol = self.volatility(

                returns

            )



            consistency = self.consistency_score(

                returns,

                max_dd,

                vol

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

                    self.total_return(

                        current_equity

                    ),

                    2

                ),



                "daily_return_percent":

                round(

                    self.daily_return(

                        returns

                    ),

                    4

                ),



                "monthly_return_percent":

                round(

                    self.monthly_return(

                        returns

                    ),

                    2

                ),



                "volatility":

                round(

                    vol * 100,

                    2

                ),



                "maximum_drawdown_percent":

                round(

                    max_dd,

                    2

                ),



                "sharpe_ratio":

                self.sharpe_ratio(

                    returns

                ),



                "sortino_ratio":

                self.sortino_ratio(

                    returns

                ),



                "recovery_factor":

                self.recovery_factor(

                    current_equity,

                    max_dd

                ),



                "consistency_score":

                consistency,



                "risk_level":

                self.risk_level(

                    max_dd,

                    vol

                ),



                "performance_grade":

                self.performance_grade(

                    consistency

                ),



                "snapshots_analyzed":

                len(history)

            }



        finally:


            self.db.close()


    # -----------------------------------------------
    # CLOSE DATABASE CONNECTION
    # -----------------------------------------------

    def close(self):

        if self.db:

            self.db.close()



# =====================================================
# API HELPER FUNCTION
# =====================================================

def get_performance_analytics() -> Dict:

    engine = PerformanceEngine()

    try:

        return engine.generate_report()

    finally:

        engine.close()