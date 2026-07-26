from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth.services.jwt import decode_token


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    try:

        payload = decode_token(
            credentials.credentials
        )

        if payload.get("role") not in {"investor", "admin"}:
            raise HTTPException(
                status_code=403,
                detail="Invalid role"
            )

        return payload


    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )


def get_current_investor(
    current=Depends(get_current_user)
):
    if current.get("role") != "investor":
        raise HTTPException(status_code=403, detail="Investor access required")
    return current
