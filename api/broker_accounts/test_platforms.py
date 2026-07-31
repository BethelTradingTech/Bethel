from api.broker_accounts.platforms import (
    TradingPlatform,
    normalize_platform,
    platform_capabilities,
)


def test_platform_aliases():
    assert normalize_platform("mt4") == TradingPlatform.MT4
    assert normalize_platform("cTrader") == TradingPlatform.CTRADER
    assert normalize_platform("match-trader") == TradingPlatform.MATCH_TRADER


def test_platform_capabilities_are_explicit():
    capabilities = platform_capabilities()
    assert {item["platform"] for item in capabilities} == {
        "MT4",
        "MT5",
        "CTRADER",
        "MATCH_TRADER",
    }
    assert all(item["mode"] == "PAPER" for item in capabilities)
    live = {item["platform"]: item["live_execution"] for item in capabilities}
    assert live == {
        "MT4": False,
        "MT5": True,
        "CTRADER": False,
        "MATCH_TRADER": False,
    }
