"""
Bethel Trading Technologies
Breakeven Protection Engine
"""


class BreakevenManager:


    def __init__(
        self,
        trigger=1000,
        buffer=4000
    ):

        self.trigger = trigger
        self.buffer = buffer



    def calculate_new_stop(
        self,
        entry_price,
        current_price,
        side
    ):


        if side == "BUY":


            profit_points = (
                current_price -
                entry_price
            )


            if profit_points >= self.trigger:

                return (
                    entry_price +
                    self.buffer
                )


        elif side == "SELL":


            profit_points = (
                entry_price -
                current_price
            )


            if profit_points >= self.trigger:

                return (
                    entry_price -
                    self.buffer
                )


        return None