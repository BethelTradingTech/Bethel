import os


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def fund_controls() -> dict:
    return {
        "platform_enabled": _flag("FUND_PLATFORM_ENABLED"),
        "simulated_execution": _flag("FUND_SIMULATED_EXECUTION", True),
        "live_deposits": _flag("FUND_LIVE_DEPOSITS"),
        "live_trading": _flag("FUND_LIVE_TRADING"),
        "live_withdrawals": _flag("FUND_LIVE_WITHDRAWALS"),
    }


def assert_safe_configuration() -> dict:
    controls = fund_controls()
    live_flags = (
        controls["live_deposits"],
        controls["live_trading"],
        controls["live_withdrawals"],
    )
    if any(live_flags):
        raise RuntimeError(
            "Live pooled-fund operations are locked in this release. "
            "Disable FUND_LIVE_DEPOSITS, FUND_LIVE_TRADING, and "
            "FUND_LIVE_WITHDRAWALS."
        )
    return controls
