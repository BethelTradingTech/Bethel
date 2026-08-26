"""Regression contract for Bethel's public Verified Track Record.

This deliberately protects the long-lived public presentation contract:
- Darwinex-style calendar matrix: Year + Jan..Dec + Year.
- Values come from the public performance APIs, never embedded account figures.
- The page refreshes automatically so a newly active owner/master is reflected.
- Backend master resolution stays dynamic and does not pin an MT5 account number.

Change this contract only when product ownership explicitly approves a new public
track-record design or data-source policy.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = (ROOT / "frontend/js/verified-track-record.js").read_text(encoding="utf-8")
RESOLVER = (ROOT / "api/services/master_account.py").read_text(encoding="utf-8")
PERFORMANCE = (ROOT / "api/performance/routes.py").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


# Fixed public presentation contract.
require('const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]' in FRONTEND,
        "Public track record must keep Jan-Dec calendar columns")
require('["Year", ...months, "Year"]' in FRONTEND,
        "Public track record must keep Year | Jan..Dec | Year matrix")
require("yearValues.reduce((factor,r)=>factor*(1+r),1)" in FRONTEND,
        "Annual return column must remain compounded from monthly returns")
require("track-positive" in FRONTEND and "track-negative" in FRONTEND,
        "Monthly matrix must distinguish positive and negative periods")

# No static performance figures or fixed account selection in the browser.
require('/performance/public-summary' in FRONTEND and '/performance/public-history' in FRONTEND,
        "Public track record must load summary and history from backend APIs")
require('cache:"no-store"' in FRONTEND,
        "Public track record must bypass stale browser caching")
require("setInterval(load, 15000)" in FRONTEND,
        "Public track record must auto-refresh every 15 seconds")
require("summaryAgain.account_number !== data.account_number" in FRONTEND,
        "Public track record must reject mixed-account data during master switches")

# Dynamic owner/master source of truth.
require("MasterTerminalRegistry.subscriber_id.is_(None)" in RESOLVER,
        "Active master resolver must prefer owner/master terminals")
require("resolve_active_master_account" in PERFORMANCE,
        "Performance API must use the dynamic active-master resolver")
require("EquitySnapshot.account_number == account" in PERFORMANCE,
        "Public history must be filtered to the resolved active master")

# Guard against future accidental account-number pinning in the resolver.
account_literals = re.findall(r'(?<![A-Za-z0-9_])[1-9][0-9]{6,11}(?![A-Za-z0-9_])', RESOLVER)
require(not account_literals,
        f"Active master resolver contains hard-coded account-like values: {account_literals}")

print("Public track-record layout and dynamic-master contract OK")
