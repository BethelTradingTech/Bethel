from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from api.auth.services.jwt import decode_token
from api.security import (
    ALGORITHM as SUBSCRIBER_ALGORITHM,
    SECRET_KEY as SUBSCRIBER_SECRET_KEY,
)
from jose import JWTError, jwt


def _get_token(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]

    return token


def require_admin(request: Request):
    token = _get_token(request)

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return payload


def require_subscriber_or_admin(request: Request, subscriber_id: int):
    token = _get_token(request)

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        admin_payload = decode_token(token)
        if admin_payload.get("role") == "admin":
            return admin_payload
    except JWTError:
        pass

    try:
        subscriber_payload = jwt.decode(
            token,
            SUBSCRIBER_SECRET_KEY,
            algorithms=[SUBSCRIBER_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if subscriber_payload.get("subscriber_id") != subscriber_id:
        raise HTTPException(status_code=403, detail="Subscriber access denied")

    return subscriber_payload



def check_auth(request: Request):


    token = _get_token(request)



    if not token:

        return RedirectResponse(
            "/login"
        )



    try:

        decode_token(token)


    except JWTError:

        return RedirectResponse(
            "/login"
        )


    return None
