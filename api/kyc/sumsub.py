import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request

from fastapi import HTTPException


BASE_URL = os.getenv("SUMSUB_BASE_URL", "https://api.sumsub.com").rstrip("/")
APP_TOKEN = os.getenv("SUMSUB_APP_TOKEN", "")
SECRET_KEY = os.getenv("SUMSUB_SECRET_KEY", "")
LEVEL_NAME = os.getenv("SUMSUB_LEVEL_NAME", "")
WEBHOOK_SECRET = os.getenv("SUMSUB_WEBHOOK_SECRET", "")


def require_configuration():
    missing = [
        name
        for name, value in (
            ("SUMSUB_APP_TOKEN", APP_TOKEN),
            ("SUMSUB_SECRET_KEY", SECRET_KEY),
            ("SUMSUB_LEVEL_NAME", LEVEL_NAME),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=503,
            detail="Sumsub KYC is not configured: " + ", ".join(missing),
        )


def signed_request(method: str, path: str, payload: dict):
    require_configuration()
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    message = timestamp.encode() + method.upper().encode() + path.encode() + body
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    request = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method.upper(),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-App-Token": APP_TOKEN,
            "X-App-Access-Ts": timestamp,
            "X-App-Access-Sig": signature,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"Sumsub API rejected the request ({error.code}): {detail}",
        ) from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach Sumsub API",
        ) from error


def generate_sdk_token(external_user_id: str, email: str | None):
    payload = {
        "userId": external_user_id,
        "levelName": LEVEL_NAME,
        "ttlInSecs": 600,
    }
    if email:
        payload["applicantIdentifiers"] = {"email": email}
    return signed_request("POST", "/resources/accessTokens/sdk", payload)


def verify_webhook(raw_body: bytes, digest: str, algorithm: str):
    if not WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="SUMSUB_WEBHOOK_SECRET is not configured",
        )
    algorithms = {
        "HMAC_SHA256_HEX": hashlib.sha256,
        "HMAC_SHA512_HEX": hashlib.sha512,
        "HMAC_SHA1_HEX": hashlib.sha1,
    }
    digest_function = algorithms.get(algorithm)
    if digest_function is None:
        raise HTTPException(status_code=400, detail="Unsupported webhook algorithm")
    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        digest_function,
    ).hexdigest()
    if not hmac.compare_digest(expected, digest or ""):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
