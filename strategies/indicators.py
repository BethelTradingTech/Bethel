"""
Bethel Trading Technologies
AuraStyle TrendHunter Indicators
"""

import ta


def calculate_indicators(data):

    # EMA Trend
    data["EMA_50"] = ta.trend.ema_indicator(
        data["close"],
        window=50
    )

    data["EMA_200"] = ta.trend.ema_indicator(
        data["close"],
        window=200
    )


    # RSI Momentum
    data["RSI"] = ta.momentum.rsi(
        data["close"],
        window=14
    )


    # ADX Trend Strength
    adx = ta.trend.ADXIndicator(
        high=data["high"],
        low=data["low"],
        close=data["close"],
        window=14
    )

    data["ADX"] = adx.adx()


    # ATR Volatility
    atr = ta.volatility.AverageTrueRange(
        high=data["high"],
        low=data["low"],
        close=data["close"],
        window=14
    )

    data["ATR"] = atr.average_true_range()


    return data