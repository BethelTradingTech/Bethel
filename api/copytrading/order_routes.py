from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.database import get_db
from api.auth.dependency import require_investor_or_admin
from api.copytrading.models import CopyOrder, CopySubscriber

router = APIRouter(prefix="/copytrading", tags=["Investor Read-Only Activity"])

@router.get("/investors/{investor_id}/orders")
def get_investor_observed_activity(
    investor_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_investor_or_admin),
):
    # Strict lookup mapping investor_id to their copy subscriber record
    subscriber = db.query(CopySubscriber).filter(
        CopySubscriber.investor_id == investor_id
    ).first()
    
    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="Subscriber not found for this investor"
        )

    # Read historical activity records for this specific subscriber
    orders = db.query(CopyOrder).filter(
        CopyOrder.subscriber_id == subscriber.id
    ).all()

    formatted_orders = []
    for order in orders:
        formatted_orders.append({
            "master_ticket": order.master_ticket,
            "symbol": order.symbol,
            "direction": order.direction,
            "volume": order.volume,
            "entry_price": order.entry_price,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "profit": order.profit if hasattr(order, "profit") else 0.0,
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "executed_at": order.executed_at.isoformat() if order.executed_at else None
        })

    return {
        "status": "success",
        "platform_access": "READ_ONLY",
        "execution_owner": "METATRADER_EA",
        "subscriber_id": subscriber.id,
        "total_observed_trades": len(formatted_orders),
        "observed_trades": formatted_orders,
        "total_orders": len(formatted_orders),
        "orders": formatted_orders,
    }