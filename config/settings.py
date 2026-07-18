"""
Bethel Trading Technologies
System Configuration
"""

COMPANY_NAME = "Bethel Trading Technologies"

VERSION = "1.0.0"

ENVIRONMENT = "DEVELOPMENT"


# Trading Risk Settings

RISK_PER_TRADE = 0.01

MAX_DAILY_LOSS = 0.04

MAX_OPEN_POSITIONS = 5


# Market Settings

DEFAULT_TIMEFRAME = "1h"

MARKETS = [
    "BTCUSDT",
    "ETHUSDT",
    "EURUSD"
]


print(f"{COMPANY_NAME} Configuration Loaded")