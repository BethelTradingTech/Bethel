from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from api.auth.dependency import require_subscriber_or_admin
from api.database import get_db
from api.kyc.native_engine import load_evidence, store_evidence
from api.kyc.native_models import BethelKYCEvidence, BethelKYCSession


router = APIRouter(prefix="/kyc", tags=["Bethel Native KYC Device Handoff"])
HANDOFF_AUDIENCE = "bethel-kyc-device-handoff"
HANDOFF_TTL_SECONDS = int(os.getenv("KYC_DEVICE_HANDOFF_TTL_SECONDS", "600"))
MAX_SELFIE_UPLOAD = int(os.getenv("KYC_MAX_UPLOAD_BYTES", "12582912"))
ALLOWED_SELFIE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
HANDOFF_CATEGORY = "handoff-selfie"


def _signing_key() -> str:
    key = (os.getenv("KYC_ENCRYPTION_KEY") or "").strip()
    if len(key) < 32:
        raise HTTPException(status_code=503, detail="KYC handoff signing is unavailable")
    return key


def _session_for(db: Session, subscriber_id: int, reference: str) -> BethelKYCSession:
    item = (
        db.query(BethelKYCSession)
        .filter(
            BethelKYCSession.subscriber_id == subscriber_id,
            BethelKYCSession.reference == reference,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Native KYC session not found")
    if item.status in {"approved", "rejected"} or item.challenge_consumed_at is not None:
        raise HTTPException(status_code=409, detail="This KYC session can no longer accept a device handoff")
    return item


def _handoff_evidence(db: Session, session_id: int) -> BethelKYCEvidence | None:
    return (
        db.query(BethelKYCEvidence)
        .filter(
            BethelKYCEvidence.session_id == session_id,
            BethelKYCEvidence.category == HANDOFF_CATEGORY,
        )
        .first()
    )


def _decode_token(token: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            _signing_key(),
            algorithms=["HS256"],
            audience=HANDOFF_AUDIENCE,
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Device handoff link is invalid or expired") from exc
    if claims.get("purpose") != "kyc_selfie_handoff":
        raise HTTPException(status_code=401, detail="Invalid device handoff purpose")
    try:
        claims["subscriber_id"] = int(claims["subscriber_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid device handoff token") from exc
    return claims


@router.post("/{subscriber_id}/native/handoff")
def create_device_handoff(
    subscriber_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    reference = str(payload.get("reference") or "").strip()
    challenge = str(payload.get("challenge") or "").strip()
    if not reference or not challenge:
        raise HTTPException(status_code=422, detail="KYC session reference and challenge are required")
    item = _session_for(db, subscriber_id, reference)
    expected = hashlib.sha256(challenge.encode()).hexdigest()
    if not secrets.compare_digest(item.challenge_hash, expected):
        raise HTTPException(status_code=409, detail="Biometric challenge is invalid")

    existing = _handoff_evidence(db, item.id)
    if existing:
        return {
            "status": "captured",
            "reference": item.reference,
            "expires_in": 0,
            "handoff_token": None,
        }

    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=HANDOFF_TTL_SECONDS)
    token = jwt.encode(
        {
            "purpose": "kyc_selfie_handoff",
            "subscriber_id": subscriber_id,
            "reference": item.reference,
            "jti": secrets.token_urlsafe(18),
            "aud": HANDOFF_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        },
        _signing_key(),
        algorithm="HS256",
    )
    return {
        "status": "waiting_for_device",
        "reference": item.reference,
        "handoff_token": token,
        "expires_in": HANDOFF_TTL_SECONDS,
    }


@router.post("/native/handoff/capture")
async def capture_handoff_selfie(
    token: str = Form(...),
    selfie: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    claims = _decode_token(token)
    subscriber_id = claims["subscriber_id"]
    reference = str(claims.get("reference") or "")
    item = _session_for(db, subscriber_id, reference)
    if _handoff_evidence(db, item.id):
        raise HTTPException(status_code=409, detail="This device handoff has already been used")

    content_type = selfie.content_type or ""
    if content_type not in ALLOWED_SELFIE_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="Live selfie must be JPEG, PNG or WebP")
    data = await selfie.read()
    if not data or len(data) > MAX_SELFIE_UPLOAD:
        raise HTTPException(status_code=413, detail="Live selfie is empty or exceeds the upload limit")

    storage_key, digest = store_evidence(subscriber_id, reference, HANDOFF_CATEGORY, data)
    row = BethelKYCEvidence(
        session_id=item.id,
        subscriber_id=subscriber_id,
        category=HANDOFF_CATEGORY,
        storage_key=storage_key,
        sha256=digest,
        content_type=content_type,
        size_bytes=len(data),
    )
    db.add(row)
    db.commit()
    return {"status": "captured", "reference": reference}


@router.get("/{subscriber_id}/native/handoff/status")
def handoff_status(
    subscriber_id: int,
    reference: str,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    item = _session_for(db, subscriber_id, reference)
    captured = _handoff_evidence(db, item.id) is not None
    return {"reference": reference, "captured": captured, "status": "captured" if captured else "waiting"}


@router.get("/{subscriber_id}/native/handoff/selfie")
def handoff_selfie(
    subscriber_id: int,
    reference: str,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    item = _session_for(db, subscriber_id, reference)
    evidence = _handoff_evidence(db, item.id)
    if not evidence:
        raise HTTPException(status_code=404, detail="No handoff selfie has been captured")
    data = load_evidence(subscriber_id, reference, HANDOFF_CATEGORY, evidence.storage_key)
    return Response(
        content=data,
        media_type=evidence.content_type,
        headers={"Cache-Control": "no-store", "Content-Disposition": "inline; filename=live-selfie"},
    )
