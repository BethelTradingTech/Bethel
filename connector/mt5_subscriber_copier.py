"""Bethel subscriber copier - permanently disabled.

Bethel's platform is read-only with respect to trading. Authorized MetaTrader
Expert Advisors exclusively manage order placement, modification, and closure.

This module is intentionally non-executing and retained only so older
installations fail closed with a clear message instead of trading.
"""

import sys

READ_ONLY_LOCKED = True
EXECUTION_OWNER = "METATRADER_EA"

def run():
    raise RuntimeError(
        "Bethel subscriber copier is permanently disabled. "
        "The Bethel platform never opens, modifies, or closes trades. "
        "Trading execution is owned exclusively by MetaTrader EAs."
    )

if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"READ-ONLY SAFETY LOCK: {exc}", file=sys.stderr)
        sys.exit(2)
