import json
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from api.daily_brief.ai_writer import ai_generation_enabled, generate_ai_brief
from api.daily_brief.routes import _require_intake_token, _validated_sources
from scripts.daily_market_brief import (
    Headline,
    parse_feed,
    publish_social,
    render_brief,
    render_social_text,
    social_publishing_ready,
)


def test_parse_rss_feed():
    xml = """<?xml version='1.0' encoding='UTF-8'?>
    <rss version='2.0'><channel><title>Example</title>
      <item><title>Stocks rise after data</title><link>https://example.com/a</link><pubDate>Mon, 31 Aug 2026 12:00:00 GMT</pubDate></item>
    </channel></rss>"""
    items = parse_feed("Example Source", xml)
    assert len(items) == 1
    assert items[0].source == "Example Source"
    assert items[0].title == "Stocks rise after data"
    assert items[0].url == "https://example.com/a"


def test_parse_atom_feed_link_href():
    xml = """<?xml version='1.0' encoding='UTF-8'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <entry><title>Dollar moves</title><link href='https://example.com/b'/><updated>2026-08-31T12:00:00Z</updated></entry>
    </feed>"""
    items = parse_feed("Atom Source", xml)
    assert len(items) == 1
    assert items[0].url == "https://example.com/b"


def test_render_brief_contains_sources_and_disclaimer():
    body = render_brief(
        [Headline(source="Example", title="Gold advances", url="https://example.com/gold")],
        {"account_number": "PUBLIC", "total_return": "12.3%", "drawdown": "4.1%"},
        [],
        now=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )
    assert "BETHEL DAILY MARKET BRIEF" in body
    assert "Gold advances" in body
    assert "Source: Example" in body
    assert "Total return: 12.3%" in body
    assert "not investment advice" in body


def test_social_text_links_back_to_public_brief():
    text = render_social_text(
        [Headline(source="Example", title="Gold advances", url="https://example.com/gold")],
        now=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )
    assert "Bethel Daily Market Brief" in text
    assert "Gold advances — Example" in text
    assert "https://betheltradingtechnologies.com/daily-market-brief.html" in text
    assert "Not investment advice" in text


def test_editorial_intake_token_fails_closed(monkeypatch):
    monkeypatch.delenv("DAILY_MARKET_BRIEF_INTAKE_TOKEN", raising=False)
    with pytest.raises(HTTPException) as missing:
        _require_intake_token(None)
    assert missing.value.status_code == 503

    monkeypatch.setenv("DAILY_MARKET_BRIEF_INTAKE_TOKEN", "expected-secret")
    with pytest.raises(HTTPException) as wrong:
        _require_intake_token("wrong-secret")
    assert wrong.value.status_code == 401

    _require_intake_token("expected-secret")


def test_editorial_sources_require_https():
    assert _validated_sources(["https://reuters.com/example", "https://reuters.com/example"]) == [
        "https://reuters.com/example"
    ]
    with pytest.raises(HTTPException) as invalid:
        _validated_sources(["http://example.com/not-secure"])
    assert invalid.value.status_code == 422


def test_social_publishing_withheld_until_enabled_and_complete(monkeypatch):
    monkeypatch.delenv("DAILY_MARKET_BRIEF_SOCIAL_PUBLISHING_ENABLED", raising=False)
    for channel in ("FACEBOOK", "INSTAGRAM", "X", "LINKEDIN", "TIKTOK", "YOUTUBE"):
        monkeypatch.setenv(f"DAILY_MARKET_BRIEF_{channel}_WEBHOOK", f"https://publisher.example/{channel.lower()}")

    assert social_publishing_ready() is False
    status = publish_social("Example brief", datetime(2026, 8, 31, tzinfo=timezone.utc))
    assert set(status.values()) == {"WITHHELD"}

    monkeypatch.setenv("DAILY_MARKET_BRIEF_SOCIAL_PUBLISHING_ENABLED", "true")
    monkeypatch.delenv("DAILY_MARKET_BRIEF_YOUTUBE_WEBHOOK", raising=False)
    assert social_publishing_ready() is False
    status = publish_social("Example brief", datetime(2026, 8, 31, tzinfo=timezone.utc))
    assert set(status.values()) == {"WITHHELD"}


def test_ai_generation_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DAILY_MARKET_BRIEF_AI_ENABLED", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "should-not-be-used")
    assert ai_generation_enabled() is False
    assert generate_ai_brief([], {}, [], datetime(2026, 8, 31, tzinfo=timezone.utc)) is None


def test_ai_generation_missing_key_falls_back(monkeypatch):
    monkeypatch.setenv("DAILY_MARKET_BRIEF_AI_ENABLED", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert generate_ai_brief([], {}, [], datetime(2026, 8, 31, tzinfo=timezone.utc)) is None


def test_ai_generation_accepts_valid_grounded_response(monkeypatch):
    monkeypatch.setenv("DAILY_MARKET_BRIEF_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DAILY_MARKET_BRIEF_AI_MODEL", "test-model")

    generated = {
        "headline": "Gold leads the market close",
        "body": (
            "Gold was the principal market development in the supplied evidence. "
            "The report remains limited to the verified headlines provided to the editorial engine. "
            "What to watch next: incoming macroeconomic developments cited by verified sources. "
            "Market information is provided for general informational purposes only and is not investment advice. "
            "Past performance does not guarantee future results."
        ),
        "social_text": "Bethel Market Close: gold led the supplied market headlines. For information only; not investment advice.",
    }

    class Response:
        ok = True
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(generated)}],
                    }
                ]
            }

    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr("api.daily_brief.ai_writer.requests.post", fake_post)
    result = generate_ai_brief(
        [
            {
                "source": "Example",
                "title": "Gold advances after macro data",
                "url": "https://example.com/gold",
                "published": "2026-08-31T20:00:00Z",
            }
        ],
        {"drawdown": "4.1%"},
        [],
        datetime(2026, 8, 31, tzinfo=timezone.utc),
    )
    assert result is not None
    assert result.model == "test-model"
    assert "SOURCES" in result.body
    assert "https://example.com/gold" in result.body
    assert len(calls) == 1
    assert calls[0][1]["headers"]["Authorization"] == "Bearer test-key"


def test_ai_generation_invalid_response_falls_back(monkeypatch):
    monkeypatch.setenv("DAILY_MARKET_BRIEF_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class Response:
        ok = True
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": "not-json"}]}
                ]
            }

    monkeypatch.setattr("api.daily_brief.ai_writer.requests.post", lambda *args, **kwargs: Response())
    assert generate_ai_brief([], {}, [], datetime(2026, 8, 31, tzinfo=timezone.utc)) is None
