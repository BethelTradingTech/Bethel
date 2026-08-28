from starlette.requests import Request

from api.traffic.routes import _client_kind, _location, _referrer_label


def _request(headers: dict[str, str]) -> Request:
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in headers.items()]
    return Request({"type": "http", "method": "POST", "path": "/traffic/visit", "headers": raw_headers})


def test_location_prefers_edge_enrichment_headers():
    request = _request(
        {
            "x-client-country": "BB",
            "x-client-region": "Saint Michael",
            "x-client-city": "Bridgetown",
            "cf-ipcountry": "US",
        }
    )
    assert _location(request) == ("BB", "Saint Michael", "Bridgetown")


def test_location_falls_back_to_cloudflare_headers():
    request = _request(
        {
            "cf-ipcountry": "GH",
            "cf-region": "Greater Accra",
            "cf-ipcity": "Accra",
        }
    )
    assert _location(request) == ("GH", "Greater Accra", "Accra")


def test_referrer_labels_direct_internal_and_external_sources():
    assert _referrer_label(None) == "Direct / None"
    assert _referrer_label("") == "Direct / None"
    assert _referrer_label("https://betheltradingtechnologies.com/performance") == "Internal"
    assert _referrer_label("https://www.google.com/search?q=bethel") == "google.com"


def test_bot_detection_stays_separate_from_human_traffic():
    browser, device, is_bot = _client_kind("Mozilla/5.0 Googlebot/2.1")
    assert is_bot is True
    assert browser == "Other"
    assert device == "Desktop"
