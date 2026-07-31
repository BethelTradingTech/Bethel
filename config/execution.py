"""Execution controls. Live trading requires both global and per-account authorization."""

import os


EXECUTION_MODE = os.getenv("BETHEL_EXECUTION_MODE", "PAPER").strip().upper()
LIVE_COPY_ENABLED = os.getenv("BETHEL_LIVE_COPY_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

if EXECUTION_MODE not in {"PAPER", "LIVE"}:
    raise RuntimeError("BETHEL_EXECUTION_MODE must be PAPER or LIVE")
if EXECUTION_MODE == "LIVE" and not LIVE_COPY_ENABLED:
    # Fail closed: a stale LIVE mode cannot bypass the emergency switch.
    EXECUTION_MODE = "PAPER"
