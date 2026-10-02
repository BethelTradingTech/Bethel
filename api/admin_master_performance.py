from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.dependency import require_super_admin
from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import (
    ConnectorCashFlow,
    ConnectorDeal,
    ConnectorPosition,
    ConnectorStatus,
    MasterTerminalRegistry,
    PublicMt5DisplaySetting,
)
from api.services.account_risk_profile import get_account_risk_profile

router = APIRouter(prefix="/admin/master-performance", tags=["Super Admin Master Performance"])


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _round(value, places=2):
    return round(float(value or 0), places)


def _month_key(value):
    return value.strftime("%Y-%m")


def _terminal(db, registry_id: int):
    terminal = db.query(MasterTerminalRegistry).filter(
        MasterTerminalRegistry.id == registry_id,
        MasterTerminalRegistry.active.is_(True),
        MasterTerminalRegistry.subscriber_id.is_(None),
    ).first()
    if terminal is None:
        raise HTTPException(404, "Owner/master terminal not found")
    return terminal


def _validated_status(db, terminal):
    """Return connector telemetry only when it belongs to the registry account."""
    status = db.query(ConnectorStatus).filter(
        ConnectorStatus.connector_id == terminal.connector_id
    ).first()
    if status is None:
        return None
    if str(status.account_number or "").strip() != str(terminal.account_number or "").strip():
        return None
    return status


def _monthly_returns(snapshots, cash_flows):
    """Legacy snapshot calculation retained for compatibility/tests only.

    Super Admin reporting uses the signed account risk-profile history below so
    that it has the same full-history source and finalized-month rule as public
    performance reporting.
    """
    current_period = datetime.now(timezone.utc).strftime("%Y-%m")
    snapshots_by_month = defaultdict(list)
    cash_by_month = defaultdict(float)
    for row in snapshots:
        key = _month_key(row.timestamp)
        if key >= current_period:
            continue
        snapshots_by_month[key].append(row)
    for row in cash_flows:
        key = _month_key(row.occurred_at)
        if key >= current_period:
            continue
        cash_by_month[key] += float(row.amount or 0)

    rows = []
    for key in sorted(snapshots_by_month):
        month = snapshots_by_month[key]
        first = month[0]
        last = month[-1]
        start_equity = float(first.equity or 0)
        end_equity = float(last.equity or 0)
        net_cash_flow = cash_by_month.get(key, 0.0)
        trading_change = end_equity - start_equity - net_cash_flow
        pct = (trading_change / start_equity * 100.0) if start_equity > 0 else None
        rows.append({
            "month": key,
            "start_equity": _round(start_equity),
            "end_equity": _round(end_equity),
            "net_cash_flow": _round(net_cash_flow),
            "trading_change": _round(trading_change),
            "return_percent": _round(pct) if pct is not None else None,
        })
    return rows


def _profile_return_report(account_number, now=None, lock_completed_months=False):
    """Expose calculation status and provisional months without inventing returns."""
    instant = now or datetime.now(timezone.utc)
    current_period = instant.strftime("%Y-%m")
    current_start = datetime(instant.year, instant.month, 1)
    account = str(account_number or "").strip()
    try:
        profile = get_account_risk_profile(account)
        finalized_profile = (
            get_account_risk_profile(account, as_of=current_start)
            if lock_completed_months else profile
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Master return calculation failed")
        return {"status": "error", "reason": "calculation_failed",
                "monthly_returns": [], "provisional_monthly_returns": [],
                "provisional_reason": "calculation_failed"}
    if not isinstance(finalized_profile, dict) or finalized_profile.get("status") != "available":
        return {"status": "not_available",
                "reason": finalized_profile.get("reason", "history_unavailable") if isinstance(finalized_profile, dict) else "history_unavailable",
                "monthly_returns": [], "provisional_monthly_returns": [],
                "provisional_reason": profile.get("reason") if isinstance(profile, dict) else "history_unavailable"}

    if lock_completed_months:
        from datetime import timedelta
        last_completed_day = (current_start - timedelta(days=1)).date().isoformat()
        if finalized_profile.get("history_end") != last_completed_day:
            return {"status": "not_available", "reason": "month_end_snapshot_missing",
                    "monthly_returns": [], "provisional_monthly_returns": [],
                    "provisional_reason": None}

    import math
    finalized, provisional = [], []
    def valid_rows(source, period_predicate):
        result = []
        for row in source if isinstance(source, list) else []:
            if not isinstance(row, dict):
                continue
            period = str(row.get("period") or "")
            try:
                datetime.strptime(period, "%Y-%m")
                if len(period) != 7 or not period_predicate(period):
                    continue
                value = float(row.get("return_percent"))
                if not math.isfinite(value):
                    continue
            except (TypeError, ValueError):
                continue
            result.append({"month": period, "return_percent": round(value, 2)})
        return sorted(result, key=lambda item: item["month"])

    finalized = valid_rows(finalized_profile.get("monthly_returns"), lambda period: period < current_period)
    provisional_reason = None
    if isinstance(profile, dict) and profile.get("status") == "available":
        if lock_completed_months:
            old_opening = finalized_profile.get("raw_opening_balance")
            new_opening = profile.get("raw_opening_balance")
            tolerance = max(float(finalized_profile.get("reconciliation_tolerance") or 0),
                            float(profile.get("reconciliation_tolerance") or 0))
            if old_opening is None or new_opening is None or abs(float(new_opening) - float(old_opening)) > tolerance:
                provisional_reason = "current_month_ledger_unreconciled"
        if provisional_reason is None:
            provisional = valid_rows(profile.get("monthly_returns"), lambda period: period == current_period)
    else:
        provisional_reason = profile.get("reason", "history_unavailable") if isinstance(profile, dict) else "history_unavailable"
    return {"status": "available",
            "reason": None if finalized else "no_finalized_months",
            "monthly_returns": finalized, "provisional_monthly_returns": provisional,
            "provisional_reason": provisional_reason}


def _finalized_profile_monthly(account_number):
    """Compatibility wrapper: finalized returns retain their existing contract."""
    return _profile_return_report(account_number)["monthly_returns"]


def _yearly_returns(monthly):
    grouped = defaultdict(list)
    for row in monthly:
        grouped[row["month"][:4]].append(row)
    result = []
    for year in sorted(grouped):
        compounded = 1.0
        usable = False
        months = {}
        for row in grouped[year]:
            month_number = int(row["month"][5:7])
            value = row["return_percent"]
            months[str(month_number)] = value
            if value is not None:
                compounded *= 1.0 + (float(value) / 100.0)
                usable = True
        result.append({
            "year": int(year),
            "months": months,
            "ytd_return_percent": _round((compounded - 1.0) * 100.0) if usable else None,
        })
    return result


class TerminalAccountReplacement(BaseModel):
    new_account_number: str = Field(min_length=5, max_length=32, pattern=r"^[0-9]+$")
    expected_current_account_number: str = Field(min_length=5, max_length=32, pattern=r"^[0-9]+$")
    confirm: bool = False


@router.get("/terminals")
def master_performance_terminals(_admin=Depends(require_super_admin)):
    db = SessionLocal()
    try:
        setting = db.query(PublicMt5DisplaySetting).filter(PublicMt5DisplaySetting.id == 1).first()
        public_id = setting.terminal_registry_id if setting and setting.enabled else None
        terminals = db.query(MasterTerminalRegistry).filter(
            MasterTerminalRegistry.active.is_(True),
            MasterTerminalRegistry.subscriber_id.is_(None),
        ).order_by(MasterTerminalRegistry.label.asc()).all()
        result = []
        for terminal in terminals:
            status = _validated_status(db, terminal)
            age = max(0, int((_now_naive() - status.received_at).total_seconds())) if status else None
            result.append({
                "registry_id": terminal.id,
                "connector_id": terminal.connector_id,
                "label": terminal.label,
                "account_number": terminal.account_number,
                "connection_status": "ONLINE" if status and age <= 150 else ("STALE" if status else "OFFLINE"),
                "account_mode": status.mode if status else None,
                "currency": status.currency if status else None,
                "balance": _round(status.balance) if status else None,
                "equity": _round(status.equity) if status else None,
                "floating_profit": _round(status.floating_profit) if status else None,
                "last_seen": status.received_at.isoformat() + "Z" if status else None,
                "is_public": terminal.id == public_id,
            })
        return {"read_only": True, "public_terminal_registry_id": public_id, "terminals": result}
    finally:
        db.close()


@router.put("/terminals/{registry_id}/account")
def replace_master_terminal_account(
    registry_id: int,
    data: TerminalAccountReplacement,
    _admin=Depends(require_super_admin),
):
    """Replace the MT5 account bound to an existing owner/master connector.

    Connector identity is preserved. Historical snapshots/deals/cash flows remain
    account-scoped and are not reassigned. Live connector cache is cleared so old
    account telemetry cannot be displayed under the replacement account while the
    connector sends its first accepted snapshot.
    """
    if not data.confirm:
        raise HTTPException(400, "Explicit confirmation is required")

    new_account = data.new_account_number.strip()
    expected_account = data.expected_current_account_number.strip()
    db = SessionLocal()
    try:
        terminal = _terminal(db, registry_id)
        current_account = str(terminal.account_number or "").strip()
        if current_account != expected_account:
            raise HTTPException(
                409,
                f"Terminal account changed since this page was loaded; current account is {current_account}",
            )
        if new_account == current_account:
            return {
                "status": "unchanged",
                "registry_id": terminal.id,
                "connector_id": terminal.connector_id,
                "old_account_number": current_account,
                "new_account_number": new_account,
            }

        conflict = db.query(MasterTerminalRegistry).filter(
            MasterTerminalRegistry.id != terminal.id,
            MasterTerminalRegistry.account_number == new_account,
            MasterTerminalRegistry.active.is_(True),
        ).first()
        if conflict is not None:
            raise HTTPException(
                409,
                f"MT5 account {new_account} is already assigned to active connector {conflict.connector_id}",
            )

        public_setting = db.query(PublicMt5DisplaySetting).filter(PublicMt5DisplaySetting.id == 1).first()
        if public_setting and public_setting.enabled and public_setting.terminal_registry_id == terminal.id:
            raise HTTPException(
                409,
                "This terminal is currently selected for the public website. Disable or change the public MT5 display before replacing its account.",
            )

        terminal.account_number = new_account
        terminal.updated_at = _now_naive()

        # These tables are current/live cache, not historical performance records.
        # Clear them so the old account cannot appear under the replacement registry.
        db.query(ConnectorPosition).filter(
            ConnectorPosition.connector_id == terminal.connector_id
        ).delete(synchronize_session=False)
        db.query(ConnectorStatus).filter(
            ConnectorStatus.connector_id == terminal.connector_id
        ).delete(synchronize_session=False)

        db.commit()
        return {
            "status": "replaced",
            "read_only": True,
            "registry_id": terminal.id,
            "connector_id": terminal.connector_id,
            "label": terminal.label,
            "old_account_number": current_account,
            "new_account_number": new_account,
            "history_reassigned": False,
            "public_display_changed": False,
            "message": "Registry updated. The running connector may now submit telemetry for the replacement MT5 account.",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/{registry_id}")
def master_performance(registry_id: int, _admin=Depends(require_super_admin)):
    db = SessionLocal()
    try:
        terminal = _terminal(db, registry_id)
        status = _validated_status(db, terminal)
        snapshots = db.query(EquitySnapshot).filter(
            EquitySnapshot.account_number == terminal.account_number
        ).order_by(EquitySnapshot.timestamp.asc()).all()
        deals = db.query(ConnectorDeal).filter(
            ConnectorDeal.connector_id == terminal.connector_id,
            ConnectorDeal.account_number == terminal.account_number,
        ).order_by(ConnectorDeal.closed_at.asc()).all()
        cash_flows = db.query(ConnectorCashFlow).filter(
            ConnectorCashFlow.connector_id == terminal.connector_id,
            ConnectorCashFlow.account_number == terminal.account_number,
        ).order_by(ConnectorCashFlow.occurred_at.asc()).all()
        positions = []
        if status is not None:
            positions = db.query(ConnectorPosition).filter(
                ConnectorPosition.connector_id == terminal.connector_id
            ).all()
        setting = db.query(PublicMt5DisplaySetting).filter(PublicMt5DisplaySetting.id == 1).first()

        return_report = _profile_return_report(
            terminal.account_number,
            # Account 01's existing demo/public calculation is deliberately unchanged.
            lock_completed_months=str(terminal.account_number) != "49617874",
        )
        monthly = return_report["monthly_returns"]
        yearly = _yearly_returns(monthly)
        pnl = lambda d: float(d.profit or 0) + float(d.commission or 0) + float(d.swap or 0) + float(d.fee or 0)
        wins = sum(1 for deal in deals if pnl(deal) > 0)
        losses = sum(1 for deal in deals if pnl(deal) < 0)
        gross_profit = sum(max(0.0, pnl(d)) for d in deals)
        gross_loss = abs(sum(min(0.0, pnl(d)) for d in deals))
        net_closed = sum(pnl(d) for d in deals)
        deposits = sum(float(c.amount or 0) for c in cash_flows if float(c.amount or 0) > 0)
        withdrawals = abs(sum(float(c.amount or 0) for c in cash_flows if float(c.amount or 0) < 0))
        age = max(0, int((_now_naive() - status.received_at).total_seconds())) if status else None

        return {
            "read_only": True,
            "terminal": {
                "registry_id": terminal.id,
                "connector_id": terminal.connector_id,
                "label": terminal.label,
                "account_number": terminal.account_number,
                "is_public": bool(setting and setting.enabled and setting.terminal_registry_id == terminal.id),
            },
            "live": {
                "connection_status": "ONLINE" if status and age <= 150 else ("STALE" if status else "OFFLINE"),
                "account_mode": status.mode if status else None,
                "currency": status.currency if status else None,
                "balance": _round(status.balance) if status else None,
                "equity": _round(status.equity) if status else None,
                "floating_profit": _round(status.floating_profit) if status else None,
                "open_position_count": len(positions),
                "last_seen": status.received_at.isoformat() + "Z" if status else None,
            },
            "history": {
                "snapshot_count": len(snapshots),
                "closed_deals": len(deals),
                "cash_flow_events": len(cash_flows),
                "net_closed_trading_pl": _round(net_closed),
                "deposits": _round(deposits),
                "withdrawals": _round(withdrawals),
                "wins": wins,
                "losses": losses,
                "win_rate_percent": _round((wins / (wins + losses) * 100.0) if wins + losses else 0),
                "profit_factor": _round(gross_profit / gross_loss) if gross_loss > 0 else None,
            },
            "monthly_returns": monthly,
            "monthly_equity_history": [],
            "yearly_returns": yearly,
            "returns_status": return_report["status"],
            "returns_reason": return_report["reason"],
            "provisional_monthly_returns": return_report["provisional_monthly_returns"],
            "provisional_reason": return_report.get("provisional_reason"),
            "return_method": (
                "signed account full-history cash-flow-neutral returns; finalized calendar months only; YTD compounds finalized monthly returns"
                if str(terminal.account_number) == "49617874" else
                "signed account cash-flow-neutral returns; completed months anchored to the last month-end snapshot; YTD compounds finalized monthly returns"
            ),
        }
    finally:
        db.close()
