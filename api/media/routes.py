from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, Query

from api.auth.dependency import require_admin
from api.database import SessionLocal
from api.models import EquitySnapshot, Trade


router = APIRouter(prefix="/media", tags=["Verified performance media"])


@router.get("/weekly-report")
def weekly_report(days: int = Query(7, ge=1, le=31), _admin=Depends(require_admin)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        points = db.query(EquitySnapshot).filter(EquitySnapshot.timestamp >= cutoff).order_by(EquitySnapshot.timestamp).all()
        if not points:
            return {"status": "insufficient_data", "period_days": days}
        start, end = points[0], points[-1]
        trades = db.query(Trade).filter(
            Trade.account_number == end.account_number,
            Trade.status == "CLOSED",
            Trade.closed_at >= cutoff,
        ).all()
        pnl = end.equity - start.equity
        return_pct = (pnl / start.equity * 100) if start.equity else 0
        wins = sum(1 for trade in trades if float(trade.profit or 0) > 0)
        peak = float(points[0].equity)
        max_dd = 0.0
        for point in points:
            peak = max(peak, float(point.equity))
            max_dd = max(max_dd, ((peak - float(point.equity)) / peak * 100) if peak else 0)
        return {
            "status": "verified",
            "account_number": end.account_number,
            "account_mode": os.getenv("MASTER_ACCOUNT_MODE", "DEMO"),
            "period_start": start.timestamp.isoformat() + "Z",
            "period_end": end.timestamp.isoformat() + "Z",
            "starting_equity": round(float(start.equity), 2),
            "ending_equity": round(float(end.equity), 2),
            "weekly_pnl": round(pnl, 2),
            "weekly_return_percent": round(return_pct, 2),
            "closed_trades": len(trades),
            "win_rate_percent": round((wins / len(trades) * 100) if trades else 0, 2),
            "maximum_drawdown_percent": round(max_dd, 2),
            "profitable": pnl > 0,
            "disclosure": "Past performance does not guarantee future results.",
        }
    finally:
        db.close()
