"""
Bethel Trading Technologies
Market Data Engine

Responsible for collecting financial market data.
"""

import ccxt
import yfinance as yf
import pandas as pd


class MarketDataEngine:


    def __init__(self):

        self.exchange = ccxt.binance()


    def get_crypto_data(self, symbol="BTC/USDT", timeframe="1h", limit=100):

        print(f"Downloading {symbol} market data...")

        candles = self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit
        )

        dataframe = pd.DataFrame(
            candles,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )

        dataframe["timestamp"] = pd.to_datetime(
            dataframe["timestamp"],
            unit="ms"
        )

        return dataframe



    def get_stock_data(self, symbol="SPY"):

        print(f"Downloading {symbol} data...")

        data = yf.download(
            symbol,
            period="1mo",
            interval="1h"
        )

        return data



if __name__ == "__main__":

    engine = MarketDataEngine()

    btc = engine.get_crypto_data()

    print(btc.head())