from fastapi import APIRouter, HTTPException

from api.database import SessionLocal
from api.daily_brief.models import DailyMarketBrief

router = APIRouter(prefix="/public/daily-market-brief", tags=["Public daily market brief"])


@router.get("/latest")
def latest_daily_market_brief():
    db = SessionLocal()
    try:
        row = db.query(DailyMarketBrief).order_by(DailyMarketBrief.brief_date.desc()).first()
        if row is None:
            raise HTTPException(status_code=404, detail="No daily market brief has been published yet")
        return {
            "brief_date": row.brief_date.isoformat(),
            "generated_at": row.generated_at.isoformat() + "Z",
            "body": row.body,
            "social_text": row.social_text,
        }
    finally:
        db.close()
