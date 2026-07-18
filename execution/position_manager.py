"""
Bethel Trading Technologies
Position Manager

Tracks active positions.
"""


class PositionManager:


    def __init__(self):

        self.positions = []



    def add_position(self, trade):

        self.positions.append(trade)



    def count_symbol_positions(self, symbol):

        count = 0

        for position in self.positions:

            if position["symbol"] == symbol:

                count += 1


        return count



    def get_positions(self):

        return self.positions



    def close_position(self, symbol):

        self.positions = [

            p for p in self.positions

            if p["symbol"] != symbol

        ]