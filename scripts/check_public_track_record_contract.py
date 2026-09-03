"""Regression contract for Bethel's public finalized monthly/yearly return display.

Current public-reporting contract:
- Show monthly and Year/YTD returns only.
- Keep the Jan-Dec calendar matrix.
- Exclude the current unfinished month.
- Calculate Year/YTD from finalized monthly returns in the backend.
- Use only the owner/master terminal explicitly selected by Super Admin.
- Never expose live account telemetry or account numbers in the browser.
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


compact_frontend = "".join(FRONTEND.split())

# Public presentation: monthly and Year/YTD returns only.
for month in ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"):
    require(f'"{month}"' in FRONTEND, f"Public returns must keep {month} calendar column")
require('"Year/YTD"' in FRONTEND or '"Year / YTD"' in FRONTEND,
        "Public returns must retain a Year/YTD column")
require("Monthly & Yearly Returns" in FRONTEND,
        "Public performance area must retain the monthly/yearly returns heading")
require("track-positive" in FRONTEND and "track-negative" in FRONTEND,
        "Monthly matrix must distinguish positive and negative periods")

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

# Public data must come from the privacy-reduced backend endpoint.
require('/performance/public-summary' in FRONTEND,
        "Public returns must load from the public performance summary API")
require("data.monthly_returns" in FRONTEND,
        "Public returns must use backend finalized monthly return history")
require("data.yearly_returns" in FRONTEND,
        "Public returns must use backend Year/YTD history")
require('cache:"no-store"' in FRONTEND,
        "Public returns must bypass stale browser caching")
require("setInterval(loadReturns,15000)" in compact_frontend,
        "Public returns must auto-refresh every 15 seconds")

# Browser must defensively exclude the unfinished current month.
require("currentPeriod" in FRONTEND and ".filter(r=>String(r.period)<currentPeriod)" in compact_frontend,
        "Public renderer must exclude the unfinished current month")

# Backend must use explicit public-master selection and finalize months server-side.
require("resolve_public_master_account" in PERFORMANCE,
        "Public performance API must use the explicit public-master resolver")
require("_finalized_monthly_returns" in PERFORMANCE,
        "Public performance API must filter unfinished monthly periods")
require("_yearly_returns_from_monthly" in PERFORMANCE,
        "Year/YTD must be calculated from finalized monthly returns in the backend")
require('"monthly_returns":monthly' in "".join(PERFORMANCE.split()) and '"yearly_returns":yearly' in "".join(PERFORMANCE.split()),
        "Public summary must return finalized monthly and yearly return series")

# Explicit Super Admin selection must remain owner/master-only and fail closed publicly.
require("MasterTerminalRegistry.subscriber_id.is_(None)" in RESOLVER,
        "Public master resolver must restrict selection to owner/master terminals")
require("def resolve_public_master_account" in RESOLVER,
        "Public master resolver must exist")
require("return _selected_public_master_account(db)" in RESOLVER,
        "Public master resolver must use only the explicit Super Admin selection")

# Public browser and resolver must never pin real MT5 account numbers.
for source_name, source in (("resolver", RESOLVER), ("public renderer", FRONTEND)):
    account_literals = re.findall(r'(?<![A-Za-z0-9_])[1-9][0-9]{6,11}(?![A-Za-z0-9_])', source)
    require(not account_literals,
            f"{source_name} contains hard-coded account-like values: {account_literals}")

# Public summary must not deliberately expose account identity or live telemetry.
public_summary_block = PERFORMANCE.split('@router.get("/public-summary")', 1)[1].split('@router.get("/public-history")', 1)[0]
for forbidden_key in (
    '"account_number"',
    '"master_account"',
    '"current_balance"',
    '"current_equity"',
    '"floating_profit_loss"',
    '"open_positions"',
):
    require(forbidden_key not in public_summary_block,
            f"Public summary must not expose {forbidden_key}")

print("Public finalized monthly/Year-YTD privacy contract OK")
