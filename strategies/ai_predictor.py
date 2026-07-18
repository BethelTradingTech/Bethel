"""
Bethel Trading Technologies
AuraStyle TrendHunter AI Predictor

Converted from MT5 EA logic
"""


def ai_predictor(data):

    score = 0


    latest = data.iloc[-1]


    fast = latest["EMA_50"]
    slow = latest["EMA_200"]

    rsi = latest["RSI"]

    adx = latest["ADX"]


    # Bullish conditions

    if fast > slow:
        score += 1


    if rsi > 50:
        score += 1


    if adx > 20:
        score += 1



    # Bearish conditions

    if fast < slow:
        score -= 1


    if rsi < 50:
        score -= 1


    if adx > 20:
        score -= 1



    if score >= 2:

        return {
            "signal": "BUY",
            "score": score,
            "confidence": "HIGH"
        }



    if score <= -2:

        return {
            "signal": "SELL",
            "score": score,
            "confidence": "HIGH"
        }



    return {
        "signal": "HOLD",
        "score": score,
        "confidence": "LOW"
    }