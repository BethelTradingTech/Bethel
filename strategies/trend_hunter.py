"""
Bethel Trading Technologies
AuraStyle TrendHunter Strategy
"""

from strategies.indicators import calculate_indicators
from strategies.ai_predictor import ai_predictor



class TrendHunter:


    def analyze(self, market_data):

        data = calculate_indicators(
            market_data
        )


        signal = ai_predictor(
            data
        )


        return signal