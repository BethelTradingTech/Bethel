from __future__ import annotations

import base64
import hashlib
import hmac
import html
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from api.auth.dependency import require_admin
from api.database import Base, SessionLocal, engine


router = APIRouter(prefix="/integrations/tiktok", tags=["TikTok Integration"])

AUTHORIZATION_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
REVOKE_URL = "https://open.tiktokapis.com/v2/oauth/revoke/"
REDIRECT_URI = "https://api.betheltradingtechnologies.com/admin/control/integrations/tiktok/callback"
STATE_MAX_AGE_SECONDS = 900
DEFAULT_SCOPES = "user.info.basic,video.upload"


class TikTokConnection(Base):
    __tablename__ = "tiktok_connections"

    id = Column(Integer, primary_key=True)
    provider = Column(String(32), nullable=False, unique=True, default="tiktok")
    open_id = Column(String(255), nullable=True)
    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    refresh_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text, nullable=True)
    connected = Column(Boolean, nullable=False, default=False)
    connected_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


TikTokConnection.__table__.create(bind=engine, checkfirst=True)


def _client_key() -> str:
    return (os.getenv("TIKTOK_CLIENT_KEY") or "").strip()


def _client_secret() -> str:
    return (os.getenv("TIKTOK_CLIENT_SECRET") or "").strip()


def _configured_scopes() -> str:
    raw = (os.getenv("TIKTOK_OAUTH_SCOPES") or DEFAULT_SCOPES).strip()
    scopes = [item.strip() for item in raw.replace(" ", ",").split(",") if item.strip()]
    return ",".join(dict.fromkeys(scopes))


def _require_credentials() -> tuple[str, str]:
    client_key, client_secret = _client_key(), _client_secret()
    if not client_key or not client_secret:
        raise HTTPException(status_code=503, detail="TikTok OAuth credentials are not configured in the production environment.")
    return client_key, client_secret


def _state_secret() -> bytes:
    secret = _client_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="TikTok OAuth client secret is not configured.")
    return secret.encode("utf-8")


def _make_state() -> str:
    issued = str(int(time.time()))
    nonce = secrets.token_urlsafe(24)
    payload = f"{issued}.{nonce}"
    signature = hmac.new(_state_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _verify_state(state: str) -> None:
    try:
        issued, nonce, signature = state.split(".", 2)
        timestamp = int(issued)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid TikTok OAuth state.")
    payload = f"{issued}.{nonce}"
    expected = hmac.new(_state_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid TikTok OAuth state signature.")
    age = int(time.time()) - timestamp
    if age < 0 or age > STATE_MAX_AGE_SECONDS:
        raise HTTPException(status_code=400, detail="TikTok OAuth state has expired. Start the connection again.")


def _fernet() -> Fernet:
    material = (os.getenv("JWT_SECRET_KEY") or _client_secret()).encode("utf-8")
    if not material:
        raise HTTPException(status_code=503, detail="Server encryption key is unavailable.")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(material).digest()))


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Stored TikTok credential could not be decrypted.") from exc


def _get_connection(db) -> TikTokConnection | None:
    return db.query(TikTokConnection).filter(TikTokConnection.provider == "tiktok").first()


def _aware(value: datetime | None) -> datetime | None:
    if value and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _safe_connection_payload(connection: TikTokConnection | None) -> dict:
    now = datetime.now(timezone.utc)
    expires = _aware(connection.token_expires_at if connection else None)
    refresh_expires = _aware(connection.refresh_token_expires_at if connection else None)
    return {
        "configured": bool(_client_key() and _client_secret()),
        "connected": bool(connection and connection.connected and connection.encrypted_access_token),
        "redirect_uri": REDIRECT_URI,
        "scopes_configured": _configured_scopes().split(",") if _configured_scopes() else [],
        "granted_scopes": [item for item in (connection.scopes or "").split(",") if item] if connection else [],
        "open_id_present": bool(connection and connection.open_id),
        "token_expires_at": expires.isoformat() if expires else None,
        "refresh_token_expires_at": refresh_expires.isoformat() if refresh_expires else None,
        "token_expired": bool(expires and expires <= now),
        "refresh_token_expired": bool(refresh_expires and refresh_expires <= now),
        "connected_at": connection.connected_at.isoformat() if connection and connection.connected_at else None,
    }


def _token_request(data: dict[str, str]) -> dict:
    try:
        response = requests.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="TikTok token service could not be reached.") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="TikTok returned an invalid token response.") from exc
    if response.status_code >= 400 or payload.get("error"):
        description = str(payload.get("error_description") or payload.get("error") or "TikTok rejected the token request.")
        raise HTTPException(status_code=502, detail=description[:500])
    return payload


def _store_token_payload(db, connection: TikTokConnection, payload: dict, now: datetime) -> None:
    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="TikTok did not return an access token.")
    refresh_token = payload.get("refresh_token")
    expires_in = int(payload.get("expires_in") or 0)
    refresh_expires_in = int(payload.get("refresh_expires_in") or 0)
    connection.encrypted_access_token = _encrypt(access_token)
    if refresh_token:
        connection.encrypted_refresh_token = _encrypt(refresh_token)
    connection.open_id = payload.get("open_id") or connection.open_id
    connection.scopes = payload.get("scope") or connection.scopes or _configured_scopes()
    connection.token_expires_at = now + timedelta(seconds=expires_in) if expires_in > 0 else None
    if refresh_expires_in > 0:
        connection.refresh_token_expires_at = now + timedelta(seconds=refresh_expires_in)
    connection.connected = True
    connection.updated_at = now


def _refresh_connection(db, connection: TikTokConnection) -> str:
    if not connection.encrypted_refresh_token:
        raise RuntimeError("TikTok refresh token is unavailable")
    refresh_expires = _aware(connection.refresh_token_expires_at)
    if refresh_expires and refresh_expires <= datetime.now(timezone.utc):
        raise RuntimeError("TikTok refresh token has expired; reconnect TikTok")
    client_key, client_secret = _require_credentials()
    payload = _token_request({
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": _decrypt(connection.encrypted_refresh_token),
    })
    now = datetime.now(timezone.utc)
    _store_token_payload(db, connection, payload, now)
    db.commit()
    return _decrypt(connection.encrypted_access_token)


@router.get("/status")
def tiktok_status(_: dict = Depends(require_admin)):
    db = SessionLocal()
    try:
        return _safe_connection_payload(_get_connection(db))
    finally:
        db.close()


@router.get("/connect")
def tiktok_connect(_: dict = Depends(require_admin)):
    client_key, _ = _require_credentials()
    scopes = _configured_scopes()
    if not scopes:
        raise HTTPException(status_code=409, detail="TikTok OAuth scopes are not configured.")
    params = {
        "client_key": client_key,
        "response_type": "code",
        "scope": scopes,
        "redirect_uri": REDIRECT_URI,
        "state": _make_state(),
    }
    return {"authorization_url": f"{AUTHORIZATION_URL}?{urlencode(params)}", "redirect_uri": REDIRECT_URI}


@router.get("/callback", response_class=HTMLResponse)
def tiktok_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    if error:
        message = html.escape(error_description or error)
        return HTMLResponse(
            f"<html><body style='font-family:system-ui;background:#0b0f19;color:#f3f4f6;padding:40px'><h2>TikTok connection was not completed</h2><p>{message}</p><p>You may close this window and return to Bethel Super Admin.</p></body></html>",
            status_code=400,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="TikTok authorization code or state is missing.")
    _verify_state(state)
    client_key, client_secret = _require_credentials()
    payload = _token_request({
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        connection = _get_connection(db)
        if connection is None:
            connection = TikTokConnection(provider="tiktok")
            db.add(connection)
        _store_token_payload(db, connection, payload, now)
        connection.connected_at = now
        db.commit()
    finally:
        db.close()

    return HTMLResponse(
        "<html><body style='font-family:system-ui;background:#0b0f19;color:#f3f4f6;padding:40px'><h2>TikTok connected successfully</h2><p>Bethel has securely stored the authorized TikTok credentials.</p><p>You may close this window and return to Bethel Super Admin.</p></body></html>"
    )


@router.post("/disconnect")
def tiktok_disconnect(_: dict = Depends(require_admin)):
    db = SessionLocal()
    try:
        connection = _get_connection(db)
        if connection and connection.encrypted_access_token:
            try:
                client_key, client_secret = _require_credentials()
                requests.post(
                    REVOKE_URL,
                    data={
                        "client_key": client_key,
                        "client_secret": client_secret,
                        "token": _decrypt(connection.encrypted_access_token),
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
                    timeout=20,
                )
            except Exception:
                pass
        if connection:
            connection.open_id = None
            connection.encrypted_access_token = None
            connection.encrypted_refresh_token = None
            connection.token_expires_at = None
            connection.refresh_token_expires_at = None
            connection.scopes = None
            connection.connected = False
            connection.updated_at = datetime.now(timezone.utc)
            db.commit()
        return {"status": "disconnected", "redirect_uri": REDIRECT_URI}
    finally:
        db.close()


def get_tiktok_access_token() -> str:
    """Internal helper for approved TikTok operations. Refreshes expiring tokens server-side and never exposes them via API."""
    db = SessionLocal()
    try:
        connection = _get_connection(db)
        if not connection or not connection.connected or not connection.encrypted_access_token:
            raise RuntimeError("TikTok is not connected")
        expires = _aware(connection.token_expires_at)
        if expires and expires <= datetime.now(timezone.utc) + timedelta(minutes=5):
            return _refresh_connection(db, connection)
        return _decrypt(connection.encrypted_access_token)
    finally:
        db.close()
