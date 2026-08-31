import hmac
import json
import os
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from api.database import SessionLocal
from api.daily_brief.models import DailyMarketBrief

router = APIRouter(tags=["Daily market brief"])


class EditorialIntake(BaseModel):
    brief_date: date
    headline: str = Field(min_length=5, max_length=240)
    body: str = Field(min_length=80, max_length=20000)
    social_text: str = Field(min_length=20, max_length=5000)
    sources: list[str] = Field(default_factory=list, max_length=20)
    generated_at: datetime | None = None


def _require_intake_token(provided: str | None) -> None:
    expected = os.getenv("DAILY_MARKET_BRIEF_INTAKE_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Daily market brief editorial intake is not configured")
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid daily market brief intake token")


def _validated_sources(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        url = value.strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise HTTPException(status_code=422, detail="All source URLs must use https")
        if url not in cleaned:
            cleaned.append(url)
    return cleaned


@router.get("/public/daily-market-brief/latest")
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


@router.post("/internal/daily-market-brief/intake")
def editorial_intake(
    payload: EditorialIntake,
    x_bethel_daily_brief_token: str | None = Header(default=None, alias="X-Bethel-Daily-Brief-Token"),
):
    """Accept one authoritative externally researched Bethel market-close brief.

    This endpoint archives the brief for the Bethel website. It deliberately does
    not send email and does not call any social publishing webhook.
    """
    _require_intake_token(x_bethel_daily_brief_token)
    sources = _validated_sources(payload.sources)
    generated_at = payload.generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is not None:
        generated_at = generated_at.astimezone(timezone.utc).replace(tzinfo=None)

    db = SessionLocal()
    try:
        row = db.query(DailyMarketBrief).filter(DailyMarketBrief.brief_date == payload.brief_date).first()
        created = row is None
        if row is None:
            row = DailyMarketBrief(brief_date=payload.brief_date)
            db.add(row)
        row.generated_at = generated_at
        row.body = payload.body.strip()
        row.social_text = payload.social_text.strip()
        row.source_health = json.dumps(
            {
                "origin": "editorial_intake",
                "headline": payload.headline.strip(),
                "sources": sources,
            },
            sort_keys=True,
        )
        row.social_status = json.dumps(
            {
                "facebook": "WITHHELD",
                "instagram": "WITHHELD",
                "x": "WITHHELD",
                "linkedin": "WITHHELD",
                "tiktok": "WITHHELD",
                "youtube": "WITHHELD",
            },
            sort_keys=True,
        )
        db.commit()
        return {
            "status": "accepted",
            "created": created,
            "brief_date": payload.brief_date.isoformat(),
            "website_archived": True,
            "email_sent": False,
            "social_publishing": "WITHHELD",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
