"""
Bethel Trading Technologies
ATR Stop Loss / Take Profit Engine
"""


def calculate_levels(
    entry_price,
    atr,
    multiplier=14,
    reward_ratio=14,
    direction="BUY"
):


    risk_distance = atr * multiplier


    if direction == "BUY":

        stop_loss = entry_price - risk_distance

        take_profit = entry_price + (
            risk_distance * reward_ratio
        )


    else:

        stop_loss = entry_price + risk_distance

        take_profit = entry_price - (
            risk_distance * reward_ratio
        )


    return {

        "stop_loss": round(stop_loss, 5),

        "take_profit": round(take_profit, 5)

    }