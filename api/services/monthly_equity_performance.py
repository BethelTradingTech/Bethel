"""Auditable completed-month equity changes and recovery for owner accounts."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import math


def realized_month_recovery(deals):
    """Dollar recovery of the deepest closed-P/L drawdown within one month.

    Funding is excluded. The curve starts at zero P/L, not account capital,
    so a depleted and subsequently funded account still has a valid result.
    Equal-time exits are grouped because the database cannot establish their
    broker execution order. This is not an equity return or Darwinex D-Score.
    """
    changes = defaultdict(float)
    for deal in deals:
        changes[deal.closed_at] += sum(float(getattr(deal, key) or 0)
                                       for key in ("profit", "commission", "swap", "fee"))
    total = peak = deepest = trough = 0.0
    for when in sorted(changes):
        total += changes[when]
        peak = max(peak, total)
        drawdown = peak - total
        if drawdown > deepest:
            deepest, trough = drawdown, total
    net = round(total, 2)
    recovered = max(0.0, total - trough) if deepest > 0 else 0.0
    return {
        "monthly_profit_result": "profit" if net > 0 else "loss" if net < 0 else "break_even",
        "realized_drawdown_amount": round(deepest, 2),
        "realized_recovered_amount": round(recovered, 2),
        "dollar_loss_recovery_percent": round(recovered / deepest * 100, 2) if deepest > 0 else None,
        "dollar_loss_recovery_status": ("fully_recovered" if recovered >= deepest else
                                        "partial" if recovered > 0 else "none") if deepest > 0 else "no_drawdown",
        "realized_profit_basis": "imported closed-deal profit, commission, swap and fee; funding excluded",
    }


def completed_month_equity(snapshots, flows, deals, now=None, monthly_returns=None):
    """Use observed boundary equity; never infer an absent opening or closing quote.

    Recovery uses an equity curve adjusted for recorded funding. This describes
    account recovery; it is not Darwinex D-Score.
    """
    current = (now or datetime.now(timezone.utc)).strftime("%Y-%m")
    returns = {row["month"]: row["return_percent"] for row in (monthly_returns or [])}
    ordered = sorted(snapshots, key=lambda s: (s.timestamp, s.id))
    by_month = defaultdict(list)
    for snapshot in ordered:
        by_month[snapshot.timestamp.strftime("%Y-%m")].append(snapshot)
    for deal in deals:
        by_month[deal.closed_at.strftime("%Y-%m")]
    result = []
    for month in sorted(key for key in by_month if key < current):
        start = datetime.strptime(month, "%Y-%m")
        end = datetime(start.year + (start.month == 12), start.month % 12 + 1, 1)
        prior = [s for s in ordered if start - timedelta(days=4) <= s.timestamp < start]
        closing = [s for s in by_month[month] if end - timedelta(days=3) <= s.timestamp < end]
        month_deals = [d for d in deals if start <= d.closed_at < end]
        closed_pl = sum(float(d.profit or 0) + float(d.commission or 0)
                        + float(d.swap or 0) + float(d.fee or 0) for d in month_deals)
        row = {"month": month, "net_closed_trading_pl": round(closed_pl, 2),
               "equity_gain": None, "recovery_percent": None,
               "recovery_grade": None, "monthly_grade": None,
               "status": "boundary_snapshot_missing"}
        row.update(realized_month_recovery(month_deals))
        if not prior or not closing:
            result.append(row)
            continue
        opening, close = prior[-1], closing[-1]
        period_flows = [f for f in flows if opening.timestamp < f.occurred_at <= close.timestamp]
        cash = sum(float(f.amount or 0) for f in period_flows)
        gain = float(close.equity) - float(opening.equity) - cash
        row.update(opening_equity=round(float(opening.equity), 2),
                   closing_equity=round(float(close.equity), 2),
                   net_cash_flow=round(cash, 2), equity_gain=round(gain, 2),
                   opening_observed_at=opening.timestamp.isoformat() + "Z",
                   closing_observed_at=close.timestamp.isoformat() + "Z",
                   status="observed_boundaries")
        balance_gap = float(close.balance) - float(opening.balance) - cash - closed_pl
        row["balance_ledger_gap"] = round(balance_gap, 2)
        if abs(balance_gap) > max(0.02, abs(float(close.balance)) * 0.0015):
            row["status"] = "ledger_gap"
        curve = [opening] + [s for s in by_month[month] if opening.timestamp < s.timestamp <= close.timestamp]
        adjusted = [float(s.equity) - sum(float(f.amount or 0) for f in period_flows
                    if f.occurred_at <= s.timestamp) for s in curve]
        low_index = min(range(len(curve)), key=lambda i: adjusted[i])
        prior_peak = max(adjusted[:low_index + 1])
        drawdown = prior_peak - adjusted[low_index]
        if drawdown > 0 and row["status"] == "observed_boundaries":
            recovered = max(0.0, adjusted[-1] - adjusted[low_index])
            row["recovery_percent"] = round(min(100.0, recovered / drawdown * 100.0), 2)
            row["recovery_grade"] = "strong" if recovered >= drawdown else "partial" if recovered > 0 else "none"
        if row["status"] == "observed_boundaries" and month in returns:
            # Grade the displayed cash-flow-neutral return, not the dollar gain.
            # A deposit following a loss can leave a positive dollar gain and
            # negative time-weighted return; grading the gain would contradict it.
            monthly_return = float(returns[month])
            base = 50.0 + 35.0 * math.tanh(monthly_return / 20.0)
            penalty = 15.0 * min(1.0, drawdown / max(prior_peak, 0.01))
            bonus = 15.0 * float(row["recovery_percent"] or 0.0) / 100.0
            score = max(0.0, min(100.0, base - penalty + bonus))
            row["monthly_score"] = round(score, 2)
            row["monthly_grade"] = "A" if score >= 80 else "B" if score >= 70 else "C" if score >= 60 else "D" if score >= 50 else "E"
        result.append(row)
    return result
