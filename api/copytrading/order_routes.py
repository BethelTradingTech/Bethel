from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.database import get_db
from api.copytrading.models import CopyOrder, CopySubscriber

router = APIRouter(prefix="/copytrading", tags=["Copy Trading"])

@router.get("/investors/{investor_id}/orders")
def get_investor_copy_orders(investor_id: int, db: Session = Depends(get_db)):
    # Strict lookup mapping investor_id to their copy subscriber record
    subscriber = db.query(CopySubscriber).filter(
        CopySubscriber.investor_id == investor_id
    ).first()
    
    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="Subscriber not found for this investor"
        )

    # Fetch all copy orders for this specific subscriber
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
        "subscriber_id": subscriber.id,
        "total_orders": len(formatted_orders),
        "orders": formatted_orders
    }