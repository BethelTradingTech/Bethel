import hashlib
import hmac
import os
import time

from fastapi import Header, HTTPException, Request


MAX_CLOCK_SKEW_SECONDS = 300


async def verify_trust_remit_signature(
    request: Request,
    x_service_timestamp: str = Header(...),
    x_service_signature: str = Header(...),
) -> None:
    secret = os.getenv("TRUST_REMIT_SERVICE_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="Trust & Remit integration is not configured")

    try:
        timestamp = int(x_service_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid service timestamp") from exc

    if abs(int(time.time()) - timestamp) > MAX_CLOCK_SKEW_SECONDS:
        raise HTTPException(status_code=401, detail="Expired service request")

    body = await request.body()
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join([
        x_service_timestamp,
        request.method.upper(),
        request.url.path,
        body_hash,
    ])
    expected = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_service_signature.lower()):
        raise HTTPException(status_code=401, detail="Invalid service signature")
