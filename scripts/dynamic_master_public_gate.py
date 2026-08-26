"""Regression gate for dynamic owner/master public return routing."""
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
    if forbidden in master or forbidden in public_js:
        raise SystemExit(f"DYNAMIC MASTER GATE FAIL: hard-coded account {forbidden}")

# Public monthly/yearly returns must always come from the dynamic backend,
# re-check the active account, and refresh frequently.
required_public = [
    "/performance/public-summary",
    "data.monthly_returns",
    "summaryAgain.account_number",
    "data.account_number",
    "active master changed during refresh",
    'cache:"no-store"',
]
for needle in required_public:
    if needle not in public_js:
        raise SystemExit(f"DYNAMIC MASTER PUBLIC GATE FAIL: missing {needle!r}")

compact_public_js = "".join(public_js.split())
if "setInterval(loadReturns,15000)" not in compact_public_js:
    raise SystemExit("DYNAMIC MASTER PUBLIC GATE FAIL: public returns must refresh every 15 seconds")

print("PASS: active owner/master and public monthly/yearly returns are dynamically synchronized")
