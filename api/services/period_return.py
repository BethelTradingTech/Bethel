"""Period-level Modified Dietz return from verified valuations and external funding.

Callers must reconcile broker history and distinguish external funding from
trading costs, credit and corrections before invoking this function. Monthly
and YTD reporting use the same function over their respective date ranges.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation


def period_return(start: datetime, end: datetime, opening_value, closing_value,
                  external_flows, *, reconciled=False):
    """Use [start, end), with flows weighted by remaining seconds in the period.

    Values are balance for realized-only reporting or equity for total reporting;
    callers must use the same basis for both boundaries and every period.
    No intermediate trade division is performed, so depletion is not itself an
    error. Missing valuations, unreconciled data and non-positive capital remain
    explicit unavailable results, never zero returns.
    """
    def unavailable(reason):
        return {"status": "not_available", "reason": reason,
                "return_percent": None, "trading_gain": None}
    if not reconciled:
        return unavailable("ledger_unreconciled")
    if opening_value is None or closing_value is None:
        return unavailable("boundary_value_missing")
    duration = Decimal(str((end - start).total_seconds()))
    if duration <= 0:
        raise ValueError("Period end must follow start")
    try:
        opening, closing = Decimal(str(opening_value)), Decimal(str(closing_value))
        net_flow = weighted_flow = Decimal(0)
        for when, raw_amount in external_flows:
            if not start <= when < end:
                raise ValueError("Funding event outside period")
            amount = Decimal(str(raw_amount))
            if not amount.is_finite():
                return unavailable("non_finite_input")
            weight = Decimal(str((end - when).total_seconds())) / duration
            net_flow += amount
            weighted_flow += weight * amount
        if not opening.is_finite() or not closing.is_finite():
            return unavailable("non_finite_input")
    except InvalidOperation:
        return unavailable("invalid_input")
    gain = closing - opening - net_flow
    capital = opening + weighted_flow
    if capital <= 0:
        return unavailable("non_positive_weighted_capital")
    return {"status": "available", "reason": None,
            "trading_gain": float(gain), "net_external_flow": float(net_flow),
            "weighted_capital": float(capital),
            "return_percent": float(gain / capital * 100),
            "method": "modified_dietz_period_return"}
