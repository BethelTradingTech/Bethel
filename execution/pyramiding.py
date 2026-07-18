"""
Bethel Trading Technologies
Dynamic Scaling / Pyramiding Engine
"""


class PyramidingManager:


    def __init__(
        self,
        max_positions=5,
        distance=8000,
        multiplier=10
    ):

        self.max_positions = max_positions
        self.distance = distance
        self.multiplier = multiplier



    def should_add_position(
        self,
        position_count,
        entry_price,
        current_price
    ):


        if position_count >= self.max_positions:

            return False



        movement = abs(
            current_price -
            entry_price
        )


        if movement >= self.distance:

            return True



        return False




    def calculate_new_size(
        self,
        current_size
    ):

        return round(
            current_size *
            self.multiplier,
            4
        )