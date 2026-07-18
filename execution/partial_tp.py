"""
Bethel Trading Technologies
Partial Take Profit Engine
"""


class PartialTakeProfit:


    def __init__(
        self,
        percent=70
    ):

        self.percent = percent



    def calculate_close_volume(
        self,
        current_volume
    ):


        close_volume = (
            current_volume *
            self.percent /
            100
        )


        remaining = (
            current_volume -
            close_volume
        )


        return {

            "close_volume": round(
                close_volume,
                4
            ),

            "remaining_volume": round(
                remaining,
                4
            )
        }