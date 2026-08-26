"""Regression contract for Bethel's public monthly/yearly return display.

Product ownership explicitly approved a simplified public presentation:
- Keep the Darwinex-style calendar matrix: Year + Jan..Dec + Year.
- Remove Super Admin-style performance analytics from the public renderer.
- Keep return values dynamic and scoped to the active owner/master account.
- Refresh automatically and reject mixed-account data during master switches.
- Never pin a real MT5 account number in browser or master-resolution code.

Internal analytics remain available in Super Admin; this contract only governs
what is rendered on the public website.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = (ROOT / "frontend/js/verified-track-record.js").read_text(encoding="utf-8")
RESOLVER = (ROOT / "api/services/master_account.py").read_text(encoding="utf-8")
PERFORMANCE = (ROOT / "api/routes/performance/router.py").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


# Fixed public presentation contract: monthly/yearly returns only.
require('const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]' in FRONTEND,
        "Public returns must keep Jan-Dec calendar columns")
require('["Year", ...months, "Year"]' in FRONTEND,
        "Public returns must keep Year | Jan..Dec | Year matrix")
require("yearValues.reduce((factor,r)=>factor*(1+r),1)" in FRONTEND,
        "Annual return column must remain compounded from monthly returns")
require("track-positive" in FRONTEND and "track-negative" in FRONTEND,
        "Monthly matrix must distinguish positive and negative periods")
require("Monthly & Yearly Returns" in FRONTEND,
        "Public performance area must retain the monthly/yearly returns heading")

# Internal Super Admin-style analytics must not be rendered publicly.
for forbidden_id in (
    "track-starting-balance",
    "track-current-balance",
    "track-current-equity",
    "track-total-return",
    "track-banked-return",
    "track-daily-return",
    "track-weekly-return",
    "track-monthly-return",
    "track-history-days",
    "track-history-start",
    "track-annualized-return",
    "track-max-dd",
    "track-current-dd",
    "track-sharpe",
    "track-sortino",
    "track-volatility",
    "track-winrate",
    "track-profit-factor",
    "track-grade",
    "track-ath",
    "track-chart-container",
):
    require(forbidden_id not in FRONTEND,
            f"Public renderer must not expose internal analytics element {forbidden_id!r}")

# Returns must stay dynamic and active-master scoped.
require('/performance/public-summary' in FRONTEND,
        "Public returns must load from the dynamic performance summary API")
require("data.monthly_returns" in FRONTEND,
        "Public returns must use backend monthly return history")
require('cache:"no-store"' in FRONTEND,
        "Public returns must bypass stale browser caching")
require("summaryAgain.account_number !== data.account_number" in FRONTEND,
        "Public returns must reject mixed-account data during master switches")
compact_frontend = "".join(FRONTEND.split())
require("setInterval(loadReturns,15000)" in compact_frontend,
        "Public returns must auto-refresh every 15 seconds")

# Backend remains dynamically resolved even though detailed analytics are not shown.
require("MasterTerminalRegistry.subscriber_id.is_(None)" in RESOLVER,
        "Active master resolver must prefer owner/master terminals")
require("resolve_active_master_account" in PERFORMANCE,
        "Performance API must use the dynamic active-master resolver")

# Guard against future accidental account-number pinning in the resolver or browser.
for source_name, source in (("resolver", RESOLVER), ("public renderer", FRONTEND)):
    account_literals = re.findall(r'(?<![A-Za-z0-9_])[1-9][0-9]{6,11}(?![A-Za-z0-9_])', source)
    require(not account_literals,
            f"{source_name} contains hard-coded account-like values: {account_literals}")

print("Public monthly/yearly returns-only dynamic-master contract OK")
