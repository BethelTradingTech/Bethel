"""Shared signed-ledger reconciliation helpers.

The connector records the account's initial funding as a cash-flow event. Therefore
reconstructing the balance immediately before the first event can legitimately
produce zero. Small residual differences can also occur because brokers may expose
balance adjustments or rounded ledger components separately from closed deals.

We allow only a tightly bounded reconciliation residual (5 basis points). Larger
mismatches still fail closed so analytics are never manufactured from incomplete
ledger data.
"""

from __future__ import annotations

import math

LEDGER_RECONCILIATION_TOLERANCE_BPS = 5.0


def reconciliation_tolerance(*values: float) -> float:
    """Return a strict, scale-aware monetary tolerance for signed-ledger checks."""
    finite = [abs(float(value)) for value in values if value is not None and math.isfinite(float(value))]
    scale = max(finite, default=1.0)
    return max(0.02, scale * (LEDGER_RECONCILIATION_TOLERANCE_BPS / 10_000.0))


def resolve_opening_balance(current_balance: float, total_change: float) -> dict:
    """Resolve the pre-ledger opening balance without rejecting a funded-from-zero account.

    A balance slightly below zero within the reconciliation tolerance is normalized
    to zero. A materially negative balance remains a hard failure.
    """
    current = float(current_balance or 0.0)
    change = float(total_change or 0.0)
    raw = current - change
    tolerance = reconciliation_tolerance(current, change)
    if not math.isfinite(raw):
        return {
            "status": "not_available",
            "reason": "invalid_reconstructed_opening_balance",
            "raw_opening_balance": None,
            "opening_balance": None,
            "tolerance": tolerance,
        }
    if raw < -tolerance:
        return {
            "status": "not_available",
            "reason": "invalid_reconstructed_opening_balance",
            "raw_opening_balance": raw,
            "opening_balance": None,
            "tolerance": tolerance,
        }
    return {
        "status": "available",
        "reason": None,
        "raw_opening_balance": raw,
        "opening_balance": max(0.0, raw),
        "tolerance": tolerance,
    }


def reconciliation_is_acceptable(gap: float, *scale_values: float) -> tuple[bool, float]:
    """Validate the final signed-ledger balance using the same strict tolerance."""
    tolerance = reconciliation_tolerance(gap, *scale_values)
    return abs(float(gap or 0.0)) <= tolerance, tolerance
