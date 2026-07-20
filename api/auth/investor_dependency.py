from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth.services.jwt import decode_token


security = HTTPBearer()


def get_current_investor(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    try:

        payload = decode_token(
            credentials.credentials
        )

        if payload.get("role") != "investor":
            raise HTTPException(
                status_code=403,
                detail="Invalid investor role"
            )

        return payload


    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )