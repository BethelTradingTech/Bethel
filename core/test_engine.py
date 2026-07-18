"""
Bethel Trading Technologies
Full Engine Test
"""


from data.market_data import MarketDataEngine

from core.trading_engine import TradingEngine



data_engine = MarketDataEngine()


data = data_engine.get_crypto_data(

    "BTC/USDT",

    "1h",

    250

)



engine = TradingEngine()



result = engine.run_cycle(

    market_data=data,

    symbol="BTC/USDT",

    balance=100000,

    equity=100000

)



print("==============================")

print("FINAL TRADE RESULT")

print("==============================")


print(result)