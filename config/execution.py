"""Permanent execution boundary for Bethel Trading Technologies.

Bethel's web/API platform is read-only with respect to trading. Authorized
Expert Advisors inside MetaTrader terminals exclusively own order placement,
modification, and closure. Server-side trading execution must remain disabled.
"""

EXECUTION_MODE = "READ_ONLY"
LIVE_COPY_ENABLED = False
TRADE_EXECUTION_ENABLED = False
SERVER_SIDE_ORDER_PLACEMENT_ENABLED = False
SERVER_SIDE_ORDER_MODIFICATION_ENABLED = False
SERVER_SIDE_ORDER_CLOSURE_ENABLED = False
EXECUTION_OWNER = "METATRADER_EA"
