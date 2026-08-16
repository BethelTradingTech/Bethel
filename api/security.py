"""
Bethel Trading Technologies
Subscriber authentication security.
"""

from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext


SECRET_KEY = os.getenv("SUBSCRIBER_JWT_SECRET_KEY", "")
if len(SECRET_KEY) < 64:
    raise RuntimeError(
        "SUBSCRIBER_JWT_SECRET_KEY must be configured with at least 64 characters"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("SUBSCRIBER_TOKEN_EXPIRE_MINUTES", "60")
)
TOKEN_ISSUER = os.getenv("SUBSCRIBER_TOKEN_ISSUER", "bethel-trading-technologies")
TOKEN_AUDIENCE = os.getenv("SUBSCRIBER_TOKEN_AUDIENCE", "bethel-subscriber")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload.update({
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "iat": now,
        "nbf": now,
        "jti": str(uuid4()),
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "token_type": "subscriber",
    })
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
