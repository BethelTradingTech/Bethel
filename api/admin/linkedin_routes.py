from __future__ import annotations

import base64
import hashlib
import hmac
import json
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


router = APIRouter(prefix="/integrations/linkedin", tags=["LinkedIn Integration"])

AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
ACCESS_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
REDIRECT_URI = "https://api.betheltradingtechnologies.com/admin/control/integrations/linkedin/callback"
STATE_MAX_AGE_SECONDS = 900


class LinkedInConnection(Base):
    __tablename__ = "linkedin_connections"

    id = Column(Integer, primary_key=True)
    provider = Column(String(32), nullable=False, unique=True, default="linkedin")
    encrypted_access_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text, nullable=True)
    connected = Column(Boolean, nullable=False, default=False)
    connected_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


LinkedInConnection.__table__.create(bind=engine, checkfirst=True)


def _client_id() -> str:
    return (os.getenv("LINKEDIN_CLIENT_ID") or "").strip()


def _client_secret() -> str:
    return (os.getenv("LINKEDIN_CLIENT_SECRET") or "").strip()


def _configured_scopes() -> str:
    return " ".join((os.getenv("LINKEDIN_OAUTH_SCOPES") or "").split())


def _require_credentials() -> tuple[str, str]:
    client_id, client_secret = _client_id(), _client_secret()
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="LinkedIn OAuth credentials are not configured in the production environment.")
    return client_id, client_secret


def _state_secret() -> bytes:
    secret = _client_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="LinkedIn OAuth client secret is not configured.")
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
        raise HTTPException(status_code=400, detail="Invalid LinkedIn OAuth state.")
    payload = f"{issued}.{nonce}"
    expected = hmac.new(_state_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid LinkedIn OAuth state signature.")
    age = int(time.time()) - timestamp
    if age < 0 or age > STATE_MAX_AGE_SECONDS:
        raise HTTPException(status_code=400, detail="LinkedIn OAuth state has expired. Start the connection again.")


def _fernet() -> Fernet:
    material = (os.getenv("JWT_SECRET_KEY") or _client_secret()).encode("utf-8")
    if not material:
        raise HTTPException(status_code=503, detail="Server encryption key is unavailable.")
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Stored LinkedIn credential could not be decrypted.") from exc


def _get_connection(db) -> LinkedInConnection | None:
    return db.query(LinkedInConnection).filter(LinkedInConnection.provider == "linkedin").first()


def _safe_connection_payload(connection: LinkedInConnection | None) -> dict:
    now = datetime.now(timezone.utc)
    expires = connection.token_expires_at if connection else None
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return {
        "configured": bool(_client_id() and _client_secret()),
        "connected": bool(connection and connection.connected and connection.encrypted_access_token),
        "redirect_uri": REDIRECT_URI,
        "scopes_configured": _configured_scopes().split() if _configured_scopes() else [],
        "token_expires_at": expires.isoformat() if expires else None,
        "token_expired": bool(expires and expires <= now),
        "connected_at": connection.connected_at.isoformat() if connection and connection.connected_at else None,
    }


@router.get("/status")
def linkedin_status(_: dict = Depends(require_admin)):
    db = SessionLocal()
    try:
        return _safe_connection_payload(_get_connection(db))
    finally:
        db.close()


@router.get("/connect")
def linkedin_connect(_: dict = Depends(require_admin)):
    client_id, _ = _require_credentials()
    scopes = _configured_scopes()
    if not scopes:
        raise HTTPException(
            status_code=409,
            detail="LinkedIn OAuth scopes are not configured yet. Wait for the required LinkedIn product permissions, then set LINKEDIN_OAUTH_SCOPES in Render.",
        )
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "state": _make_state(),
        "scope": scopes,
    }
    return {"authorization_url": f"{AUTHORIZATION_URL}?{urlencode(params)}", "redirect_uri": REDIRECT_URI}


@router.get("/callback", response_class=HTMLResponse)
def linkedin_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    if error:
        message = error_description or error
        return HTMLResponse(
            f"<html><body style='font-family:system-ui;background:#0b0f19;color:#f3f4f6;padding:40px'><h2>LinkedIn connection was not completed</h2><p>{message}</p><p>You may close this window and return to Bethel Super Admin.</p></body></html>",
            status_code=400,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="LinkedIn authorization code or state is missing.")
    _verify_state(state)
    client_id, client_secret = _require_credentials()

    try:
        response = requests.post(
            ACCESS_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="LinkedIn token exchange could not be reached.") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="LinkedIn rejected the token exchange. Review the redirect URL, permissions, and application approval status.")

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="LinkedIn returned an invalid token response.") from exc

    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="LinkedIn did not return an access token.")

    expires_in = int(payload.get("expires_in") or 0)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in) if expires_in > 0 else None
    granted_scope = payload.get("scope") or _configured_scopes()

    db = SessionLocal()
    try:
        connection = _get_connection(db)
        if connection is None:
            connection = LinkedInConnection(provider="linkedin")
            db.add(connection)
        connection.encrypted_access_token = _encrypt(access_token)
        connection.token_expires_at = expires_at
        connection.scopes = granted_scope
        connection.connected = True
        connection.connected_at = now
        connection.updated_at = now
        db.commit()
    finally:
        db.close()

    return HTMLResponse(
        "<html><body style='font-family:system-ui;background:#0b0f19;color:#f3f4f6;padding:40px'><h2>LinkedIn connected successfully</h2><p>Bethel has securely stored the authorized LinkedIn access token.</p><p>You may close this window and return to Bethel Super Admin.</p></body></html>"
    )


@router.post("/disconnect")
def linkedin_disconnect(_: dict = Depends(require_admin)):
    db = SessionLocal()
    try:
        connection = _get_connection(db)
        if connection:
            connection.encrypted_access_token = None
            connection.token_expires_at = None
            connection.scopes = None
            connection.connected = False
            connection.updated_at = datetime.now(timezone.utc)
            db.commit()
        return {"status": "disconnected", "redirect_uri": REDIRECT_URI}
    finally:
        db.close()


def get_linkedin_access_token() -> str:
    """Internal helper for approved LinkedIn publishing code. Never expose this value in an API response."""
    db = SessionLocal()
    try:
        connection = _get_connection(db)
        if not connection or not connection.connected or not connection.encrypted_access_token:
            raise RuntimeError("LinkedIn is not connected")
        expires = connection.token_expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires and expires <= datetime.now(timezone.utc):
            raise RuntimeError("LinkedIn access token has expired")
        return _decrypt(connection.encrypted_access_token)
    finally:
        db.close()
