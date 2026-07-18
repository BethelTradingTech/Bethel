"""
Bethel Trading Technologies
Risk Engine Test
"""

from risk.position_sizing import PositionSizer


sizer = PositionSizer(
    risk_percent=1
)


lot = sizer.calculate_position_size(
    balance=100000,
    stop_loss_distance=500,
    price=64000
)


print("==============================")
print("BETHEL POSITION SIZE TEST")
print("==============================")

print("Calculated Position:", lot)