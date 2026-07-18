from execution.partial_tp import PartialTakeProfit


manager = PartialTakeProfit(
    percent=70
)


result = manager.calculate_close_volume(
    2
)


print("==============================")
print("PARTIAL TP TEST")
print("==============================")

print(result)