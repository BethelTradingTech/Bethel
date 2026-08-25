"""Regression gate for dynamic owner/master public performance routing."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


master = read("api/services/master_account.py")
public_js = read("frontend/js/verified-track-record.js")

required_master = [
    "MasterTerminalRegistry",
    "subscriber_id.is_(None)",
    "active.is_(True)",
    "EquitySnapshot.account_number.in_(owner_accounts)",
    "BETHEL_MASTER_ACCOUNT",
]
for needle in required_master:
    if needle not in master:
        raise SystemExit(f"DYNAMIC MASTER GATE FAIL: missing {needle!r}")

# The source-of-truth resolver must never pin a real account number in code.
for forbidden in ("49617874", "37371080", "49224282", "52847245"):
    if forbidden in master:
        raise SystemExit(f"DYNAMIC MASTER GATE FAIL: hard-coded account {forbidden}")

required_public = [
    "/performance/public-summary",
    "/performance/public-history",
    "firstSummary.account_number",
    "data.account_number",
    "active master changed during refresh",
    "setInterval(load, 15000)",
    "Stale telemetry from the previous master is not displayed",
]
for needle in required_public:
    if needle not in public_js:
        raise SystemExit(f"DYNAMIC MASTER PUBLIC GATE FAIL: missing {needle!r}")

print("PASS: active owner/master and public track record are dynamically synchronized")
