"""Bethel Daily Market Brief.

Runs as a weekday cron job, prefers an authenticated editorial brief already
archived for the trading day, and otherwise can enhance selected public RSS/Atom
feeds with a fail-safe AI editorial pass before falling back to the original
deterministic renderer. It can email the authoritative brief and can dispatch a
concise social version only after social publishing is explicitly enabled and
every configured channel webhook is present.

The job is intentionally isolated from MT5 execution and CopyHub. It never
opens, modifies, or closes trades.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests

from api.database import SessionLocal, engine
from api.daily_brief.ai_writer import generate_ai_brief
from api.daily_brief.models import DailyMarketBrief
from api.notifications.emailer import record_and_send


DEFAULT_FEEDS = (
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("CNBC Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
)
SOCIAL_CHANNELS = ("facebook", "instagram", "x", "linkedin", "tiktok", "youtube")
USER_AGENT = "BethelDailyMarketBrief/1.3 (+https://betheltradingtechnologies.com)"
PUBLIC_BRIEF_URL = os.getenv(
    "DAILY_MARKET_BRIEF_PUBLIC_URL",
    "https://betheltradingtechnologies.com/daily-market-brief.html",
).strip()
MAX_HEADLINES = max(3, min(15, int(os.getenv("DAILY_MARKET_BRIEF_MAX_HEADLINES", "8"))))
REQUEST_TIMEOUT = max(3, min(30, int(os.getenv("DAILY_MARKET_BRIEF_TIMEOUT_SECONDS", "10"))))


@dataclass(frozen=True)
class Headline:
    source: str
    title: str
    url: str
    published: str = ""


def _clean(value: str | None) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _safe_https_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Daily market brief feed URLs must use https")
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        raise ValueError("Local feed URLs are not allowed")
    return value.strip()


def configured_feeds() -> tuple[tuple[str, str], ...]:
    raw = os.getenv("DAILY_MARKET_BRIEF_FEEDS", "").strip()
    if not raw:
        return DEFAULT_FEEDS
    feeds: list[tuple[str, str]] = []
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        name, separator, url = entry.partition("|")
        if not separator:
            raise ValueError("DAILY_MARKET_BRIEF_FEEDS entries must be Name|https://url")
        feeds.append((_clean(name)[:80] or "Market source", _safe_https_url(url)))
    if not feeds:
        raise ValueError("No valid daily market brief feeds configured")
    return tuple(feeds)


def _first_text(element: ET.Element, names: Iterable[str]) -> str:
    for child in list(element):
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in names and child.text:
            value = _clean(child.text)
            if value:
                return value
    return ""


def parse_feed(source: str, xml_text: str) -> list[Headline]:
    root = ET.fromstring(xml_text)
    items: list[Headline] = []
    for node in root.iter():
        local = node.tag.rsplit("}", 1)[-1].lower()
        if local not in {"item", "entry"}:
            continue
        title = _first_text(node, {"title"})
        published = _first_text(node, {"pubdate", "published", "updated"})
        url = _first_text(node, {"link"})
        if not url:
            for child in list(node):
                if child.tag.rsplit("}", 1)[-1].lower() == "link":
                    candidate = child.attrib.get("href", "").strip()
                    if candidate:
                        url = candidate
                        break
        if not title or not url:
            continue
        if urlparse(url).scheme not in {"http", "https"}:
            continue
        items.append(Headline(source=source, title=title[:240], url=url, published=published[:120]))
    return items


def fetch_headlines() -> tuple[list[Headline], list[str]]:
    collected: list[Headline] = []
    errors: list[str] = []
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, text/xml, application/xml"}
    for source, url in configured_feeds():
        try:
            response = requests.get(_safe_https_url(url), headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            collected.extend(parse_feed(source, response.text))
        except Exception as exc:
            errors.append(f"{source}: {type(exc).__name__}: {str(exc)[:160]}")
    unique: list[Headline] = []
    seen: set[str] = set()
    for item in collected:
        fingerprint = hashlib.sha256(f"{item.title.lower()}|{item.url}".encode("utf-8")).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(item)
        if len(unique) >= MAX_HEADLINES:
            break
    return unique, errors


def fetch_bethel_snapshot() -> dict:
    base = os.getenv("BETHEL_PUBLIC_API_BASE", "https://api.betheltradingtechnologies.com").rstrip("/")
    try:
        response = requests.get(f"{base}/performance/public-summary", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _snapshot_lines(snapshot: dict) -> list[str]:
    if not snapshot:
        return ["Bethel public performance snapshot: temporarily unavailable."]
    account = snapshot.get("account_number") or snapshot.get("account") or "selected public master"
    lines = [f"Bethel public performance snapshot ({account}):"]
    mappings = (
        ("Total return", "total_return"),
        ("Monthly return", "monthly_return"),
        ("Drawdown", "drawdown"),
        ("Balance", "balance"),
        ("Equity", "equity"),
    )
    added = 0
    for label, key in mappings:
        value = snapshot.get(key)
        if value is None:
            continue
        lines.append(f"- {label}: {value}")
        added += 1
    if not added:
        lines.append("- Public summary is available; detailed headline metrics were not returned in the expected fields.")
    return lines


def render_brief(headlines: list[Headline], snapshot: dict, errors: list[str], now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    lines = ["BETHEL DAILY MARKET BRIEF", now.strftime("%A, %d %B %Y"), "", "MARKET HEADLINES"]
    if headlines:
        for index, item in enumerate(headlines, 1):
            lines.append(f"{index}. {item.title}")
            lines.append(f"   Source: {item.source}")
            lines.append(f"   {item.url}")
    else:
        lines.append("No verified feed headlines were available when this brief was generated.")
    lines.extend(["", *(_snapshot_lines(snapshot)), ""])
    if errors:
        lines.append(f"Source health: {len(errors)} configured feed(s) were temporarily unavailable; the brief continued with available sources.")
        lines.append("")
    lines.extend([
        "Bethel Trading Technologies",
        "Market information is provided for general informational purposes only and is not investment advice.",
        "Past performance does not guarantee future results.",
    ])
    return "\n".join(lines).strip() + "\n"


def render_social_text(headlines: list[Headline], now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    lines = [f"Bethel Daily Market Brief — {now:%d %b %Y}"]
    for item in headlines[:4]:
        lines.append(f"• {item.title} — {item.source}")
    if not headlines:
        lines.append("Market headline feeds were temporarily unavailable when today's brief was generated.")
    lines.extend([PUBLIC_BRIEF_URL, "For information only. Not investment advice. #BethelTradingTech #MarketBrief"])
    return "\n".join(lines)


def recipients() -> list[str]:
    raw = os.getenv("DAILY_MARKET_BRIEF_RECIPIENTS", "").strip()
    if not raw:
        return []
    values = []
    for item in re.split(r"[,;]", raw):
        address = item.strip()
        if address and "@" in address and address not in values:
            values.append(address)
    return values


def _safe_email_diagnostic(status: str, error: str | None) -> str:
    if status == "SMTP_NOT_CONFIGURED":
        return "smtp_not_configured"
    value = (error or "").lower()
    if "auth" in value or "username and password" in value or "credentials" in value:
        return "smtp_authentication"
    if "timed out" in value or "timeout" in value:
        return "smtp_timeout"
    if "ssl" in value or "tls" in value or "certificate" in value:
        return "smtp_tls"
    if "name or service not known" in value or "getaddrinfo" in value or "nodename nor servname" in value:
        return "smtp_dns"
    if "connection refused" in value:
        return "smtp_connection_refused"
    if "network is unreachable" in value or "no route to host" in value:
        return "smtp_network"
    if "sender" in value and ("refused" in value or "rejected" in value):
        return "smtp_sender_rejected"
    if "recipient" in value and ("refused" in value or "rejected" in value):
        return "smtp_recipient_rejected"
    if status == "FAILED":
        return "smtp_failed_other"
    return status.lower() if status else "unknown"


def social_publishing_ready() -> bool:
    enabled = os.getenv("DAILY_MARKET_BRIEF_SOCIAL_PUBLISHING_ENABLED", "false").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return False
    return all(os.getenv(f"DAILY_MARKET_BRIEF_{channel.upper()}_WEBHOOK", "").strip() for channel in SOCIAL_CHANNELS)


def publish_social(text: str, now: datetime) -> dict[str, str]:
    if not social_publishing_ready():
        return {channel: "WITHHELD" for channel in SOCIAL_CHANNELS}

    results: dict[str, str] = {}
    token = os.getenv("DAILY_MARKET_BRIEF_SOCIAL_WEBHOOK_TOKEN", "").strip()
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for channel in SOCIAL_CHANNELS:
        url = os.getenv(f"DAILY_MARKET_BRIEF_{channel.upper()}_WEBHOOK", "").strip()
        try:
            safe_url = _safe_https_url(url)
            response = requests.post(
                safe_url,
                json={
                    "channel": channel,
                    "title": f"Bethel Daily Market Brief — {now:%Y-%m-%d}",
                    "text": text,
                    "url": PUBLIC_BRIEF_URL,
                    "published_date": now.date().isoformat(),
                },
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            results[channel] = "SENT"
        except Exception as exc:
            results[channel] = f"FAILED:{type(exc).__name__}"
    return results


def archive_brief(
    db,
    now: datetime,
    body: str,
    social_text: str,
    errors: list[str],
    social_status: dict[str, str],
    *,
    origin: str = "rss_fallback",
    ai_model: str | None = None,
) -> None:
    DailyMarketBrief.__table__.create(bind=engine, checkfirst=True)
    row = db.query(DailyMarketBrief).filter(DailyMarketBrief.brief_date == now.date()).first()
    if row is None:
        row = DailyMarketBrief(brief_date=now.date())
        db.add(row)
    row.generated_at = now.replace(tzinfo=None)
    row.body = body
    row.social_text = social_text
    metadata: dict[str, object] = {"origin": origin, "errors": errors}
    if ai_model:
        metadata["ai_model"] = ai_model
    row.source_health = json.dumps(metadata, sort_keys=True)
    row.social_status = json.dumps(social_status, sort_keys=True)


def _is_editorial_intake(row: DailyMarketBrief | None) -> bool:
    if row is None or not row.source_health:
        return False
    try:
        metadata = json.loads(row.source_health)
    except (TypeError, ValueError):
        return False
    return isinstance(metadata, dict) and metadata.get("origin") == "editorial_intake"


def _headline_evidence(headlines: list[Headline]) -> list[dict[str, str]]:
    return [
        {
            "source": item.source,
            "title": item.title,
            "url": item.url,
            "published": item.published,
        }
        for item in headlines
        if item.url.startswith("https://")
    ]


def run() -> int:
    now = datetime.now(timezone.utc)
    targets = recipients()
    db = SessionLocal()
    try:
        DailyMarketBrief.__table__.create(bind=engine, checkfirst=True)
        existing = db.query(DailyMarketBrief).filter(DailyMarketBrief.brief_date == now.date()).first()
        editorial = _is_editorial_intake(existing)

        if editorial:
            body = existing.body
            social_text = existing.social_text
            headlines: list[Headline] = []
            errors: list[str] = []
            social_status = publish_social(social_text, now)
            existing.social_status = json.dumps(social_status, sort_keys=True)
            source_label = "editorial_intake"
        else:
            headlines, errors = fetch_headlines()
            snapshot = fetch_bethel_snapshot()
            ai_brief = generate_ai_brief(_headline_evidence(headlines), snapshot, errors, now)
            if ai_brief is not None:
                body = ai_brief.body
                social_text = ai_brief.social_text
                source_label = "ai_rss"
                ai_model = ai_brief.model
            else:
                body = render_brief(headlines, snapshot, errors, now=now)
                social_text = render_social_text(headlines, now=now)
                source_label = "rss_fallback"
                ai_model = None
            social_status = publish_social(social_text, now)
            archive_brief(
                db,
                now,
                body,
                social_text,
                errors,
                social_status,
                origin=source_label,
                ai_model=ai_model,
            )

        sent = 0
        for recipient in targets:
            delivery = record_and_send(
                db,
                recipient=recipient,
                message_type="DAILY_MARKET_BRIEF",
                subject=f"Bethel Daily Market Brief — {now:%Y-%m-%d}",
                text_body=body,
                deduplication_key=f"daily-market-brief:{now:%Y-%m-%d}:{recipient.lower()}",
            )
            if delivery.status == "SENT":
                sent += 1
            else:
                print(
                    "Daily Market Brief email diagnostic: "
                    f"status={delivery.status}; reason={_safe_email_diagnostic(delivery.status, delivery.error)}"
                )
        db.commit()

        attempted_social = [value for value in social_status.values() if value != "WITHHELD"]
        failed_social = [value for value in attempted_social if value != "SENT"]
        if attempted_social:
            social_summary = f"{sum(1 for value in attempted_social if value == 'SENT')}/{len(attempted_social)} sent"
        else:
            social_summary = "WITHHELD"
        print(
            f"Bethel Daily Market Brief complete: source={source_label}; website archived; "
            f"{sent}/{len(targets)} email(s) sent; social={social_summary}; "
            f"{len(headlines)} fallback headline(s); {len(errors)} feed error(s)."
        )
        email_failed = bool(targets and sent != len(targets))
        return 1 if email_failed or failed_social else 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run())
