"""
Bethel Trading Technologies
Backtest Test
"""


from data.market_data import MarketDataEngine

from backtesting.engine import BacktestEngine



data_engine = MarketDataEngine()



data = data_engine.get_crypto_data(

    "BTC/USDT",

    "1h",

    500

)



engine = BacktestEngine(
    starting_balance=100000
)



result = engine.run(

    data,

    "BTC/USDT"

)


print("==============================")
print("FINAL RESULTS")
print("==============================")


print(
    result.get_summary()
)