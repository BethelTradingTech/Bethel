from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from api.auth.services.jwt import decode_token
from api.security import (
    ALGORITHM as SUBSCRIBER_ALGORITHM,
    SECRET_KEY as SUBSCRIBER_SECRET_KEY,
    TOKEN_AUDIENCE as SUBSCRIBER_TOKEN_AUDIENCE,
    TOKEN_ISSUER as SUBSCRIBER_TOKEN_ISSUER,
)
from jose import JWTError, jwt


def _get_token(request: Request):
    """Prefer explicit bearer auth, then hardened admin/subscriber cookies."""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1]

    return (
        request.cookies.get("access_token")
        or request.cookies.get("subscriber_access_token")
    )


ADMIN_ROLES = {"admin", "super_admin"}


def require_admin(request: Request):
    token = _get_token(request)

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    return payload


def require_super_admin(request: Request):
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return payload


def require_subscriber_or_admin(request: Request, subscriber_id: int):
    token = _get_token(request)

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        admin_payload = decode_token(token)
        if admin_payload.get("role") in ADMIN_ROLES:
            return admin_payload
    except JWTError:
        pass

    try:
        subscriber_payload = jwt.decode(
            token,
            SUBSCRIBER_SECRET_KEY,
            algorithms=[SUBSCRIBER_ALGORITHM],
            audience=SUBSCRIBER_TOKEN_AUDIENCE,
            issuer=SUBSCRIBER_TOKEN_ISSUER,
            options={"require": ["exp", "iat", "nbf", "jti", "iss", "aud"]},
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if subscriber_payload.get("token_type") != "subscriber" or not subscriber_payload.get("jti"):
        raise HTTPException(status_code=401, detail="Invalid subscriber token")

    if subscriber_payload.get("subscriber_id") != subscriber_id:
        raise HTTPException(status_code=403, detail="Subscriber access denied")

    return subscriber_payload


def check_auth(request: Request):
    token = _get_token(request)

    if not token:
        return RedirectResponse("/login")

    try:
        payload = decode_token(token)
        if payload.get("role") not in ADMIN_ROLES:
            return RedirectResponse("/login")
    except JWTError:
        return RedirectResponse("/login")

    return None


def require_investor_or_admin(request: Request, investor_id: int):
    """Allow administrators or the investor who owns the requested record."""
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("role") in ADMIN_ROLES:
        return payload
    if payload.get("role") != "investor" or payload.get("investor_id") != investor_id:
        raise HTTPException(status_code=403, detail="Investor access denied")
    return payload
