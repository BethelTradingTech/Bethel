"""Fail-closed MT5 adapter.

Bethel is intentionally read-only. Trading is performed only by authorized
Expert Advisors running inside MetaTrader terminals.
"""


class MT5Order:
    def __init__(self, *, target_login: str, target_server: str):
        self.target_login = str(target_login).strip()
        self.target_server = str(target_server).strip()

    def send_order(
        self,
        symbol,
        side,
        volume,
        stop_loss=None,
        take_profit=None,
    ):
        return {
            "status": "disabled",
            "mode": "EA_MANAGED",
            "message": (
                "Bethel cannot place broker orders. "
                "Execution is managed exclusively by authorized MT4/MT5 EAs."
            ),
            "account": self.target_login,
            "server": self.target_server,
        }
