"""
Risk Manager Test
"""

from risk.risk_manager import RiskManager



manager = RiskManager()



result = manager.evaluate_trade(
    signal="BUY",
    balance=100000,
    equity=100500,
    stop_loss_distance=500
)


print("==============================")
print("BETHEL RISK MANAGER")
print("==============================")

print(result)