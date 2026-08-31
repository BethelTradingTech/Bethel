from datetime import datetime, timezone

from scripts.daily_market_brief import Headline, parse_feed, render_brief, render_social_text


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
