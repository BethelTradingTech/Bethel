from backtesting.metrics import PerformanceMetrics


trades = [

    {"pnl":500},
    {"pnl":-200},
    {"pnl":800},
    {"pnl":-100},
    {"pnl":300}

]


metrics = PerformanceMetrics(trades)

result = metrics.calculate()


print("==============================")
print("BETHEL PERFORMANCE METRICS")
print("==============================")

for key,value in result.items():
    print(f"{key}: {value}")