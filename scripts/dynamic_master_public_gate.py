"""Regression gate for explicit owner/master public return routing.

The public website must use only the owner/master terminal explicitly selected
by Super Admin. Snapshot recency must never auto-switch the public report source,
and the browser must never receive or compare real MT5 account numbers.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


master = read("api/services/master_account.py")
public_js = read("frontend/js/verified-track-record.js")
performance = read("api/routes/performance/router.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"PUBLIC MASTER GATE FAIL: {message}")


# Explicit Super Admin selection is the public source of truth.
for needle in (
    "MasterTerminalRegistry",
    "PublicMt5DisplaySetting",
    "MasterTerminalRegistry.subscriber_id.is_(None)",
    "MasterTerminalRegistry.active.is_(True)",
    "def resolve_public_master_account",
    "return _selected_public_master_account(db)",
):
    require(needle in master, f"missing {needle!r}")

# Internal bootstrap fallback may exist, but public resolution must fail closed.
public_resolver = master.split("def resolve_public_master_account", 1)[1].split("def resolve_active_master_account", 1)[0]
require("BETHEL_MASTER_ACCOUNT" not in public_resolver,
        "public resolver must not fall back to BETHEL_MASTER_ACCOUNT")
require("EquitySnapshot" not in master,
        "master resolver must not use snapshot recency to auto-switch accounts")

# Public summary must use the public resolver and expose only finalized returns.
public_summary = performance.split('@router.get("/public-summary")', 1)[1].split('@router.get("/public-history")', 1)[0]
compact_summary = "".join(public_summary.split())
for needle in (
    "_public_master_account()",
    "_finalized_monthly_returns",
    "_yearly_returns_from_monthly",
):
    require(needle in public_summary, f"public summary missing {needle!r}")
require('"monthly_returns":monthly' in compact_summary,
        "public summary must return finalized monthly returns")
require('"yearly_returns":yearly' in compact_summary,
        "public summary must return finalized yearly/YTD returns")

for forbidden_key in (
    '"account_number"',
    '"master_account"',
    '"current_balance"',
    '"current_equity"',
    '"floating_profit_loss"',
    '"open_positions"',
):
    require(forbidden_key not in public_summary,
            f"public summary exposes forbidden field {forbidden_key}")

# Browser consumes monthly/yearly returns without account identity.
for needle in (
    "/performance/public-summary",
    "data.monthly_returns",
    "data.yearly_returns",
    'cache:"no-store"',
):
    require(needle in public_js, f"public renderer missing {needle!r}")

compact_public_js = "".join(public_js.split())
require("setInterval(loadReturns,15000)" in compact_public_js,
        "public returns must refresh every 15 seconds")
require("data.account_number" not in public_js and "summaryAgain.account_number" not in public_js,
        "browser must not receive or compare public MT5 account numbers")
require("currentPeriod" in public_js and ".filter(r=>String(r.period)<currentPeriod)" in compact_public_js,
        "browser must exclude the unfinished current month")

# Guard against future accidental account-number pinning in public-selection code.
for source_name, source in (("resolver", master), ("public renderer", public_js)):
    account_literals = re.findall(r'(?<![A-Za-z0-9_])[1-9][0-9]{6,11}(?![A-Za-z0-9_])', source)
    require(not account_literals,
            f"{source_name} contains hard-coded account-like values: {account_literals}")

print("PASS: explicit Super Admin public-master selection and finalized return privacy are enforced")
