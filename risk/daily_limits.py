"""
Bethel Trading Technologies
Daily Risk Controller
"""


class DailyRiskManager:


    def __init__(
        self,
        start_balance,
        profit_target=10000,
        loss_limit=-1500
    ):

        self.start_balance = start_balance
        self.profit_target = profit_target
        self.loss_limit = loss_limit



    def check_daily_limit(self, equity):

        daily_profit = equity - self.start_balance


        if daily_profit >= self.profit_target:

            return {
                "status": "BLOCK",
                "reason": "Daily profit target reached"
            }



        if daily_profit <= self.loss_limit:

            return {
                "status": "BLOCK",
                "reason": "Daily loss limit reached"
            }



        return {
            "status": "ALLOW",
            "reason": "Risk limits OK"
        }