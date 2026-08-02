"""Execution controls: Bethel is permanently read-only.

Authorized Expert Advisors inside MetaTrader terminals manage all order
placement, modification, and closure.
"""

EXECUTION_MODE = "PAPER"
LIVE_COPY_ENABLED = False
TRADE_EXECUTION_ENABLED = False
EXECUTION_OWNER = "METATRADER_EA"
