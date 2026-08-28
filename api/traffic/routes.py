import hashlib
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.dependency import require_super_admin
from api.database import get_db
from api.traffic.models import WebsiteTrafficEvent

router = APIRouter(prefix="/traffic", tags=["Website Traffic Analytics"])


class VisitSchema(BaseModel):
    path: str = Field(default="/", max_length=255)
    referrer: str | None = Field(default=None, max_length=500)


def _clean_header(request: Request, *names: str) -> str | None:
    for name in names:
        value = (request.headers.get(name) or "").strip()
        if value and value.lower() not in {"unknown", "null", "none", "-"}:
            return value
    return None


def _client_ip(request: Request) -> str:
    cf = _clean_header(request, "cf-connecting-ip")
    if cf:
        return cf
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def _visitor_hash(request: Request) -> str:
    salt = os.getenv("TRAFFIC_ANALYTICS_SALT") or os.getenv("SECRET_KEY") or "bethel-traffic"
    raw = f"{_client_ip(request)}|{request.headers.get('user-agent', '')}|{salt}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _location(request: Request) -> tuple[str | None, str | None, str | None]:
    # Cloudflare Pages Function forwards request.cf values through x-client-*.
    # Direct API requests can also use Cloudflare/Vercel visitor-location headers.
    country = _clean_header(
        request,
        "x-client-country",
        "cf-ipcountry",
        "x-vercel-ip-country",
    )
    region = _clean_header(
        request,
        "x-client-region",
        "cf-region",
        "cf-region-code",
        "x-vercel-ip-country-region",
    )
    city = _clean_header(
        request,
        "x-client-city",
        "cf-ipcity",
        "x-vercel-ip-city",
    )
    return country, region, city


def _client_kind(user_agent: str) -> tuple[str, str, bool]:
    ua = (user_agent or "").lower()
    is_bot = any(token in ua for token in ("bot", "crawler", "spider", "slurp", "headless", "preview"))
    if "edg/" in ua:
        browser = "Edge"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox/" in ua:
        browser = "Firefox"
    elif "safari/" in ua and "chrome/" not in ua:
        browser = "Safari"
    else:
        browser = "Other"
    if any(token in ua for token in ("iphone", "android", "mobile")):
        device = "Mobile"
    elif any(token in ua for token in ("ipad", "tablet")):
        device = "Tablet"
    else:
        device = "Desktop"
    return browser, device, is_bot


def _top(values, limit=10):
    return [{"name": name, "count": count} for name, count in Counter(value for value in values if value).most_common(limit)]


def _referrer_label(referrer: str | None) -> str:
    if not referrer:
        return "Direct / None"
    try:
        parsed = urlparse(referrer)
        host = (parsed.hostname or "").lower()
        if not host:
            return "Direct / None"
        if host == "betheltradingtechnologies.com" or host.endswith(".betheltradingtechnologies.com"):
            return "Internal"
        return host.removeprefix("www.")
    except Exception:
        return "Other"


@router.post("/visit", status_code=202)
def record_visit(data: VisitSchema, request: Request, db: Session = Depends(get_db)):
    browser, device, is_bot = _client_kind(request.headers.get("user-agent", ""))
    country, region, city = _location(request)
    db.add(
        WebsiteTrafficEvent(
            visitor_hash=_visitor_hash(request),
            path=(data.path or "/")[:255],
            referrer=(data.referrer or request.headers.get("referer") or "")[:500] or None,
            country=country,
            region=region,
            city=city,
            browser=browser,
            device=device,
            is_bot=is_bot,
        )
    )
    db.commit()
    return {"accepted": True}


@router.get("/admin/summary")
def admin_summary(
    days: int = 7,
    _admin=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    days = max(1, min(days, 365))
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    rows = (
        db.query(WebsiteTrafficEvent)
        .filter(WebsiteTrafficEvent.created_at >= start)
        .order_by(WebsiteTrafficEvent.created_at.desc())
        .all()
    )
    human = [row for row in rows if not row.is_bot]
    online_cutoff = now - timedelta(minutes=5)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    by_day = Counter(row.created_at.date().isoformat() for row in human if row.created_at)
    city_count = sum(1 for row in human if row.city)
    country_count = sum(1 for row in human if row.country)
    return {
        "period_days": days,
        "total_page_views": len(human),
        "unique_visitors": len({row.visitor_hash for row in human}),
        "visitors_today": len({row.visitor_hash for row in human if row.created_at and row.created_at >= today_start}),
        "online_now": len({row.visitor_hash for row in human if row.created_at and row.created_at >= online_cutoff}),
        "bot_requests": len(rows) - len(human),
        "countries": _top(row.country for row in human),
        "cities": _top((f"{row.city}, {row.country}" if row.city and row.country else row.city) for row in human),
        "top_pages": _top(row.path for row in human),
        "referrers": _top(_referrer_label(row.referrer) for row in human),
        "devices": _top(row.device for row in human),
        "browsers": _top(row.browser for row in human),
        "daily": [{"date": day, "views": by_day[day]} for day in sorted(by_day)],
        "location_coverage": {
            "country_pct": round((country_count / len(human) * 100), 1) if human else 0.0,
            "city_pct": round((city_count / len(human) * 100), 1) if human else 0.0,
        },
        "recent": [
            {
                "time": row.created_at,
                "path": row.path,
                "country": row.country,
                "region": row.region,
                "city": row.city,
                "device": row.device,
                "browser": row.browser,
            }
            for row in human[:25]
        ],
        "privacy": "Raw visitor IP addresses are not stored; visitor identifiers are one-way hashed. Location is coarse city/region/country metadata supplied by the edge network.",
    }
