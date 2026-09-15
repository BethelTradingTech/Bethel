from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

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


def _finalized_profile_monthly(account_number):
    """Use the same signed full-history engine and completed-month rule as public reporting."""
    current_period = datetime.now(timezone.utc).strftime("%Y-%m")
    try:
        profile = get_account_risk_profile(str(account_number or "").strip())
    except Exception:
        return []
    if not isinstance(profile, dict) or profile.get("status") != "available":
        return []

    rows = []
    for row in profile.get("monthly_returns", []) if isinstance(profile.get("monthly_returns"), list) else []:
        period = str(row.get("period") or "")
        if len(period) != 7 or period[4] != "-" or period >= current_period:
            continue
        try:
            value = round(float(row.get("return_percent")), 2)
        except (TypeError, ValueError):
            continue
        rows.append({"month": period, "return_percent": value})
    rows.sort(key=lambda item: item["month"])
    return rows


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

        monthly = _finalized_profile_monthly(terminal.account_number)
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
            "yearly_returns": yearly,
            "return_method": "signed account full-history cash-flow-neutral returns; finalized calendar months only; YTD compounds finalized monthly returns",
        }
    finally:
        db.close()
