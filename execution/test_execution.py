"""
Bethel Trading Technologies
Full Trading Cycle Test
"""


from execution.order_manager import OrderManager
from execution.stop_manager import calculate_levels
from execution.position_manager import PositionManager



orders = OrderManager()

positions = PositionManager()



entry = 64000

atr = 100



levels = calculate_levels(

    entry_price=entry,

    atr=atr,

    direction="BUY"

)



trade = orders.open_trade(

    symbol="BTC/USDT",

    side="BUY",

    size=2,

    stop_loss=levels["stop_loss"],

    take_profit=levels["take_profit"]

)



positions.add_position(trade)



print("==============================")

print("ACTIVE POSITIONS")

print("==============================")


print(
    positions.get_positions()
)