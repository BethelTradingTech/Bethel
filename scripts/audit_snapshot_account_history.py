"""Audit and safely backfill legacy equity snapshots missing account_number.

Dry-run is the default. The tool refuses to write if another labelled account
exists in the candidate period or if the legacy series does not join the first
labelled snapshot with reasonable balance/equity continuity.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Allow direct execution with:
# .venv\Scripts\python.exe scripts\audit_snapshot_account_history.py ...
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import SessionLocal
from api.models import EquitySnapshot


def _number(value):
    return None if value is None else float(value)


def audit(account_number: str) -> dict:
    db = SessionLocal()
    try:
        labelled = (
            db.query(EquitySnapshot)
            .filter(EquitySnapshot.account_number == account_number)
            .order_by(EquitySnapshot.timestamp.asc(), EquitySnapshot.id.asc())
            .all()
        )
        if not labelled:
            return {"status": "blocked", "reason": "no_labelled_snapshots_for_account"}

        first = labelled[0]
        legacy = (
            db.query(EquitySnapshot)
            .filter(
                EquitySnapshot.timestamp < first.timestamp,
                (EquitySnapshot.account_number.is_(None)) | (EquitySnapshot.account_number == ""),
            )
            .order_by(EquitySnapshot.timestamp.asc(), EquitySnapshot.id.asc())
            .all()
        )
        conflicting = (
            db.query(EquitySnapshot.account_number)
            .filter(
                EquitySnapshot.timestamp < first.timestamp,
                EquitySnapshot.account_number.isnot(None),
                EquitySnapshot.account_number != "",
                EquitySnapshot.account_number != account_number,
            )
            .distinct()
            .all()
        )
        conflicts = sorted({str(row[0]) for row in conflicting if row[0]})
        last_legacy = legacy[-1] if legacy else None

        balance_gap_pct = None
        equity_gap_pct = None
        if last_legacy:
            balance_base = max(abs(float(first.balance or 0)), 1.0)
            equity_base = max(abs(float(first.equity or 0)), 1.0)
            balance_gap_pct = abs(float(first.balance) - float(last_legacy.balance)) / balance_base * 100
            equity_gap_pct = abs(float(first.equity) - float(last_legacy.equity)) / equity_base * 100

        issues = []
        if not legacy:
            issues.append("no_unlabelled_snapshots_before_first_labelled_snapshot")
        if conflicts:
            issues.append("conflicting_labelled_accounts_exist_before_cutover")
        if last_legacy and (balance_gap_pct > 25 or equity_gap_pct > 25):
            issues.append("legacy_to_labelled_value_gap_exceeds_25_percent")

        return {
            "status": "safe_to_apply" if not issues else "review_required",
            "account_number": account_number,
            "first_labelled_snapshot": {
                "id": first.id,
                "timestamp": first.timestamp.isoformat(),
                "balance": _number(first.balance),
                "equity": _number(first.equity),
            },
            "legacy_snapshot_count": len(legacy),
            "legacy_first_at": legacy[0].timestamp.isoformat() if legacy else None,
            "legacy_last_at": last_legacy.timestamp.isoformat() if last_legacy else None,
            "legacy_last_balance": _number(last_legacy.balance) if last_legacy else None,
            "legacy_last_equity": _number(last_legacy.equity) if last_legacy else None,
            "balance_gap_percent": round(balance_gap_pct, 4) if balance_gap_pct is not None else None,
            "equity_gap_percent": round(equity_gap_pct, 4) if equity_gap_pct is not None else None,
            "conflicting_accounts": conflicts,
            "issues": issues,
        }
    finally:
        db.close()


def apply_backfill(account_number: str) -> dict:
    report = audit(account_number)
    if report.get("status") != "safe_to_apply":
        return {"status": "blocked", "audit": report}

    cutoff = datetime.fromisoformat(report["first_labelled_snapshot"]["timestamp"])
    db = SessionLocal()
    try:
        rows = (
            db.query(EquitySnapshot)
            .filter(
                EquitySnapshot.timestamp < cutoff,
                (EquitySnapshot.account_number.is_(None)) | (EquitySnapshot.account_number == ""),
            )
            .all()
        )
        for row in rows:
            row.account_number = account_number
        db.commit()
        return {"status": "success", "updated": len(rows), "account_number": account_number}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = apply_backfill(args.account) if args.apply else audit(args.account)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
