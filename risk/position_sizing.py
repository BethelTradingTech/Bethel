"""
Bethel Trading Technologies
Position Sizing Engine

Converted from AuraStyle TrendHunter EA
"""


class PositionSizer:


    def __init__(
        self,
        risk_percent=1.0
    ):

        self.risk_percent = risk_percent



    def calculate_position_size(
        self,
        balance,
        stop_loss_distance,
        price
    ):


        risk_amount = (
            balance *
            self.risk_percent /
            100
        )


        if stop_loss_distance <= 0:

            return 0



        position_size = (
            risk_amount /
            stop_loss_distance
        )


        return round(
            position_size,
            4
        )