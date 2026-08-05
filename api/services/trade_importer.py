"""Bethel Trading Technologies - MT5 closed-trade importer."""

from datetime import datetime
from typing import Optional

from api.database import SessionLocal
from api.models import Trade
from mt5_connector.account import MT5Account
from mt5_connector.history import MT5History


def _active_account_id(explicit_account_id: Optional[int] = None) -> int:
    """Return the currently logged-in MT5 account as the trade account key."""
    if explicit_account_id is not None:
        return int(explicit_account_id)

    account = MT5Account().get_account_info()
    if account.get("status") != "connected" or not account.get("login"):
        raise RuntimeError("Active MT5 master account is unavailable")

    return int(account["login"])


def import_mt5_history(account_id: Optional[int] = None, days: int = 3650):
    """Import closed MT5 positions idempotently for the active master account."""
    db = SessionLocal()

    try:
        active_account_id = _active_account_id(account_id)
        history = MT5History().get_history(days=days)

        if history.get("status") != "success":
            return history

        positions = {}
        for deal in history.get("history", []):
            position_id = deal.get("position_id")
            if not position_id:
                continue
            positions.setdefault(position_id, []).append(deal)

        imported = 0
        skipped = 0

        for position_id, trade_deals in positions.items():
            exists = (
                db.query(Trade)
                .filter(
                    Trade.account_id == active_account_id,
                    Trade.ticket == str(position_id),
                )
                .first()
            )
            if exists:
                skipped += 1
                continue

            entry_deals = [d for d in trade_deals if d.get("entry") == 0]
            exit_deals = [d for d in trade_deals if d.get("entry") == 1]
            if not entry_deals or not exit_deals:
                continue

            entry = sorted(entry_deals, key=lambda d: d.get("time", ""))[0]
            exit_deal = sorted(exit_deals, key=lambda d: d.get("time", ""))[-1]

            net_profit = sum(
                float(d.get("profit", 0) or 0)
                + float(d.get("commission", 0) or 0)
                + float(d.get("swap", 0) or 0)
                for d in trade_deals
            )

            trade = Trade(
                account_id=active_account_id,
                ticket=str(position_id),
                symbol=entry.get("symbol", ""),
                direction=str(entry.get("type", "")),
                lot_size=float(entry.get("volume", 0) or 0),
                entry_price=float(entry.get("price", 0) or 0),
                exit_price=float(exit_deal.get("price", 0) or 0),
                profit=net_profit,
                status="CLOSED",
                opened_at=datetime.fromisoformat(entry["time"]),
                closed_at=datetime.fromisoformat(exit_deal["time"]),
            )
            db.add(trade)
            imported += 1

        db.commit()
        return {
            "status": "success",
            "account_id": active_account_id,
            "imported": imported,
            "skipped_existing": skipped,
            "positions_found": len(positions),
        }

    except Exception as exc:
        db.rollback()
        return {"status": "failed", "message": str(exc)}
    finally:
        db.close()
