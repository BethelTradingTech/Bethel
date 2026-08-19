from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, Query

from api.auth.dependency import require_admin
from api.database import SessionLocal
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorDeal


router = APIRouter(prefix="/media", tags=["Verified performance media"])
MAX_VIDEO_TRADES = 5


def _safe_recent_trades(deals):
    """Return only fields that are safe to render in authenticated media.

    Never expose connector identifiers, broker credentials, tokens, database IDs,
    order IDs, position IDs, or deal tickets through the media payload.
    """
    recent = sorted(deals, key=lambda deal: deal.closed_at, reverse=True)[:MAX_VIDEO_TRADES]
    return [
        {
            "symbol": deal.symbol,
            "direction": deal.deal_type,
            "volume": round(float(deal.volume or 0), 2),
            "price": round(float(deal.price or 0), 8),
            "net_profit": round(
                float(deal.profit or 0)
                + float(deal.commission or 0)
                + float(deal.swap or 0)
                + float(deal.fee or 0),
                2,
            ),
            "closed_at": deal.closed_at.isoformat() + "Z",
        }
        for deal in recent
    ]


@router.get("/weekly-report")
def weekly_report(days: int = Query(7, ge=1, le=31), _admin=Depends(require_admin)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        points = db.query(EquitySnapshot).filter(EquitySnapshot.timestamp >= cutoff).order_by(EquitySnapshot.timestamp).all()
        if not points:
            return {"status": "insufficient_data", "period_days": days}
        start, end = points[0], points[-1]
        deals = db.query(ConnectorDeal).filter(ConnectorDeal.closed_at >= cutoff).all()
        trade_results = {}
        for deal in deals:
            trade_results.setdefault(deal.position_id, 0.0)
            trade_results[deal.position_id] += float(deal.profit or 0) + float(deal.commission or 0) + float(deal.swap or 0) + float(deal.fee or 0)
        pnl = end.equity - start.equity
        return_pct = (pnl / start.equity * 100) if start.equity else 0
        wins = sum(1 for result in trade_results.values() if result > 0)
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
            "closed_trades": len(trade_results),
            "realized_net_profit": round(sum(trade_results.values()), 2),
            "win_rate_percent": round((wins / len(trade_results) * 100) if trade_results else 0, 2),
            "maximum_drawdown_percent": round(max_dd, 2),
            "recent_trades": _safe_recent_trades(deals),
            "profitable": pnl > 0,
            "disclosure": "Past performance does not guarantee future results.",
        }
    finally:
        db.close()
