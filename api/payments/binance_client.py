import base64
import hashlib
import hmac
import json
import os
import secrets
import string
import time
import urllib.error
import urllib.request

from fastapi import HTTPException


BASE_URL = os.getenv("BINANCE_PAY_BASE_URL", "https://bpay.binanceapi.com").rstrip("/")
API_KEY = os.getenv("BINANCE_PAY_API_KEY", "")
SECRET_KEY = os.getenv("BINANCE_PAY_SECRET_KEY", "")
PUBLIC_KEY_FILE = os.getenv("BINANCE_PAY_PUBLIC_KEY_FILE", "")


def require_configuration():
    missing = [
        name
        for name, value in (
            ("BINANCE_PAY_API_KEY", API_KEY),
            ("BINANCE_PAY_SECRET_KEY", SECRET_KEY),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=503,
            detail="Binance Pay is not configured: " + ", ".join(missing),
        )


def request_nonce():
    alphabet = string.ascii_letters
    return "".join(secrets.choice(alphabet) for _ in range(32))


def signed_post(path: str, payload: dict):
    require_configuration()
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    timestamp = str(int(time.time() * 1000))
    nonce = request_nonce()
    signing_payload = f"{timestamp}\n{nonce}\n{body}\n"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_payload.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest().upper()
    request = urllib.request.Request(
        BASE_URL + path,
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "BinancePay-Timestamp": timestamp,
            "BinancePay-Nonce": nonce,
            "BinancePay-Certificate-SN": API_KEY,
            "BinancePay-Signature": signature,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"Binance Pay rejected the request ({error.code}): {detail}",
        ) from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach Binance Pay",
        ) from error
    if result.get("status") != "SUCCESS":
        raise HTTPException(
            status_code=502,
            detail=result.get("errorMessage") or result.get("code") or "Binance Pay error",
        )
    return result.get("data") or {}


def verify_webhook(raw_body: bytes, timestamp: str, nonce: str, signature: str):
    if not PUBLIC_KEY_FILE:
        raise HTTPException(
            status_code=503,
            detail="BINANCE_PAY_PUBLIC_KEY_FILE is not configured",
        )
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as error:
        raise HTTPException(
            status_code=503,
            detail="Python cryptography package is required for Binance webhooks",
        ) from error
    try:
        with open(PUBLIC_KEY_FILE, "rb") as stream:
            public_key = serialization.load_pem_public_key(stream.read())
        payload = (
            timestamp.encode("utf-8")
            + b"\n"
            + nonce.encode("utf-8")
            + b"\n"
            + raw_body
            + b"\n"
        )
        public_key.verify(
            base64.b64decode(signature),
            payload,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid Binance webhook signature") from error
