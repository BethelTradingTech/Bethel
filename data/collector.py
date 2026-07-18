"""
Bethel Trading Technologies
Market Data Collector
"""

from market_data import MarketDataEngine
from storage import save_market_data



def run():

    engine = MarketDataEngine()

    btc_data = engine.get_crypto_data(
        "BTC/USDT",
        "1h",
        100
    )

    save_market_data(
        btc_data
    )


if __name__ == "__main__":

    run()