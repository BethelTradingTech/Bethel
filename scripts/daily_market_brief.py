"""Bethel Daily Market Brief.

Runs as a weekday cron job, reads a small set of public RSS/Atom business feeds,
adds a read-only Bethel public-performance snapshot when available, and sends a
plain-text briefing through the existing Bethel SMTP delivery layer.

The job is intentionally isolated from MT5 execution and CopyHub. It never
opens, modifies, or closes trades.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests

from api.database import SessionLocal
from api.notifications.emailer import record_and_send


DEFAULT_FEEDS = (
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("CNBC Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
)

USER_AGENT = "BethelDailyMarketBrief/1.0 (+https://betheltradingtechnologies.com)"
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
    lines = [
        "BETHEL DAILY MARKET BRIEF",
        now.strftime("%A, %d %B %Y"),
        "",
        "MARKET HEADLINES",
    ]
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

    lines.extend(
        [
            "Bethel Trading Technologies",
            "Market information is provided for general informational purposes only and is not investment advice.",
            "Past performance does not guarantee future results.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


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


def run() -> int:
    now = datetime.now(timezone.utc)
    headlines, errors = fetch_headlines()
    snapshot = fetch_bethel_snapshot()
    body = render_brief(headlines, snapshot, errors, now=now)

    targets = recipients()
    if not targets:
        print(body)
        print("DAILY_MARKET_BRIEF_RECIPIENTS is not configured; generated brief was not emailed.", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
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
        db.commit()
        print(f"Bethel Daily Market Brief complete: {sent}/{len(targets)} email(s) sent; {len(headlines)} headline(s); {len(errors)} feed error(s).")
        return 0 if sent == len(targets) else 1
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run())
