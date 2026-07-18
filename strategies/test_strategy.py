"""
AuraStyle TrendHunter Test
"""

from data.market_data import MarketDataEngine
from strategies.trend_hunter import TrendHunter


def main():

    engine = MarketDataEngine()

    btc_data = engine.get_crypto_data(
        "BTC/USDT",
        "1h",
        250
    )

    strategy = TrendHunter()

    result = strategy.analyze(
        btc_data
    )

    print("==============================")
    print("BETHEL TRENDHUNTER SIGNAL")
    print("==============================")

    print(result)


if __name__ == "__main__":
    main()