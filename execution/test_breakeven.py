from execution.breakeven import BreakevenManager


manager = BreakevenManager()


new_stop = manager.calculate_new_stop(
    entry_price=64000,
    current_price=66000,
    side="BUY"
)


print("==============================")
print("BREAKEVEN TEST")
print("==============================")


print("New Stop Loss:", new_stop)