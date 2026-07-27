import hashlib
import hmac
import json
import os
import time
from urllib import error, parse, request

from fastapi import HTTPException


STRIPE_API_BASE = os.getenv("STRIPE_API_BASE", "https://api.stripe.com").rstrip("/")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


def create_checkout_session(fields: dict) -> dict:
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY is not configured")
    body = parse.urlencode(fields).encode("utf-8")
    api_request = request.Request(
        f"{STRIPE_API_BASE}/v1/checkout/sessions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with request.urlopen(api_request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            message = payload.get("error", {}).get("message", "Stripe rejected the request")
        except Exception:
            message = "Stripe rejected the request"
        raise HTTPException(status_code=502, detail=message) from exc
    except error.URLError as exc:
        raise HTTPException(status_code=502, detail="Unable to reach Stripe") from exc


def verify_webhook(raw_body: bytes, signature_header: str) -> dict:
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="STRIPE_WEBHOOK_SECRET is not configured",
        )
    values = {}
    for part in (signature_header or "").split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            values.setdefault(key, []).append(value)
    timestamp = (values.get("t") or [None])[0]
    signatures = values.get("v1") or []
    if not timestamp or not signatures:
        raise HTTPException(status_code=401, detail="Missing Stripe webhook signature")
    try:
        event_time = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Stripe timestamp") from exc
    if abs(int(time.time()) - event_time) > 300:
        raise HTTPException(status_code=401, detail="Expired Stripe webhook signature")
    signed_payload = timestamp.encode("ascii") + b"." + raw_body
    expected = hmac.new(
        STRIPE_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected, supplied) for supplied in signatures):
        raise HTTPException(status_code=401, detail="Invalid Stripe webhook signature")
    try:
        return json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook JSON") from exc
