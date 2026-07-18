"""
Bethel Trading Technologies
Master Risk Manager

Controls trade approval before execution.
"""

from risk.daily_limits import DailyRiskManager
from risk.position_sizing import PositionSizer



class RiskManager:


    def __init__(self):

        self.daily = DailyRiskManager(
            start_balance=100000,
            profit_target=10000,
            loss_limit=-1500
        )


        self.position = PositionSizer(
            risk_percent=1
        )



    def evaluate_trade(
        self,
        signal,
        balance,
        equity,
        stop_loss_distance
    ):


        # Check daily limits

        daily_check = self.daily.check_daily_limit(
            equity
        )


        if daily_check["status"] == "BLOCK":

            return {
                "approved": False,
                "reason": daily_check["reason"]
            }



        # Ignore HOLD signals

        if signal == "HOLD":

            return {
                "approved": False,
                "reason": "No trading signal"
            }



        size = self.position.calculate_position_size(
            balance,
            stop_loss_distance,
            price=0
        )


        return {

            "approved": True,

            "signal": signal,

            "position_size": size,

            "reason": "Risk checks passed"

        }