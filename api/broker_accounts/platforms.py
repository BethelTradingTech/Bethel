"""Trading-platform registry for Bethel's non-custodial copy infrastructure."""

from enum import Enum

from fastapi import HTTPException


class TradingPlatform(str, Enum):
    MT4 = "MT4"
    MT5 = "MT5"
    CTRADER = "CTRADER"
    MATCH_TRADER = "MATCH_TRADER"


_ALIASES = {
    "MT4": TradingPlatform.MT4,
    "METATRADER4": TradingPlatform.MT4,
    "METATRADER 4": TradingPlatform.MT4,
    "MT5": TradingPlatform.MT5,
    "METATRADER5": TradingPlatform.MT5,
    "METATRADER 5": TradingPlatform.MT5,
    "CTRADER": TradingPlatform.CTRADER,
    "C TRADER": TradingPlatform.CTRADER,
    "MATCHTRADER": TradingPlatform.MATCH_TRADER,
    "MATCH TRADER": TradingPlatform.MATCH_TRADER,
    "MATCH-TRADER": TradingPlatform.MATCH_TRADER,
    "MATCH_TRADER": TradingPlatform.MATCH_TRADER,
}


PLATFORM_CAPABILITIES = {
    TradingPlatform.MT4: {
        "display_name": "MetaTrader 4",
        "authorization": "BRIDGE_AGENT",
        "live_execution": False,
    },
    TradingPlatform.MT5: {
        "display_name": "MetaTrader 5",
        "authorization": "LOCAL_TERMINAL",
        "live_execution": True,
    },
    TradingPlatform.CTRADER: {
        "display_name": "cTrader",
        "authorization": "OAUTH",
        "live_execution": False,
    },
    TradingPlatform.MATCH_TRADER: {
        "display_name": "Match-Trader",
        "authorization": "BROKER_API",
        "live_execution": False,
    },
}


def normalize_platform(value: str) -> TradingPlatform:
    normalized = " ".join(str(value or "").strip().upper().replace("_", " ").split())
    platform = _ALIASES.get(normalized)
    if platform is None:
        supported = ", ".join(item.value for item in TradingPlatform)
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported trading platform. Supported platforms: {supported}",
        )
    return platform


def platform_capabilities():
    return [
        {
            "platform": platform.value,
            **capabilities,
            "mode": "PAPER",
        }
        for platform, capabilities in PLATFORM_CAPABILITIES.items()
    ]
