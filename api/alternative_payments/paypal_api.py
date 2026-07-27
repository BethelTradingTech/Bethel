import base64
import json
import os
from urllib import error, parse, request

from fastapi import HTTPException


PAYPAL_BASE_URL = os.getenv(
    "PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com"
).rstrip("/")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")


def configured() -> bool:
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)


def api_call(path: str, method: str = "GET", payload=None) -> dict:
    if not configured():
        raise HTTPException(
            status_code=503,
            detail="PayPal sandbox credentials are not configured",
        )
    credentials = base64.b64encode(
        f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode("utf-8")
    ).decode("ascii")
    token_request = request.Request(
        f"{PAYPAL_BASE_URL}/v1/oauth2/token",
        data=parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with request.urlopen(token_request, timeout=20) as response:
            token = json.loads(response.read().decode("utf-8"))["access_token"]
    except (error.HTTPError, error.URLError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="PayPal authentication failed") from exc

    body = None if payload is None else json.dumps(payload).encode("utf-8")
    api_request = request.Request(
        f"{PAYPAL_BASE_URL}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": os.urandom(16).hex(),
        },
    )
    try:
        with request.urlopen(api_request, timeout=25) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except error.HTTPError as exc:
        try:
            result = json.loads(exc.read().decode("utf-8"))
            message = result.get("message", "PayPal rejected the request")
        except Exception:
            message = "PayPal rejected the request"
        raise HTTPException(status_code=502, detail=message) from exc
    except error.URLError as exc:
        raise HTTPException(status_code=502, detail="Unable to reach PayPal") from exc


def create_order(payload: dict) -> dict:
    return api_call("/v2/checkout/orders", "POST", payload)


def capture_order(order_id: str) -> dict:
    return api_call(f"/v2/checkout/orders/{order_id}/capture", "POST", {})
