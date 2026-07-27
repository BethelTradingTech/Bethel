"""Disabled legacy username/password authentication compatibility module."""

from datetime import datetime, timedelta
import os

from jose import jwt
from passlib.context import CryptContext


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if len(SECRET_KEY) < 64:
    raise RuntimeError("JWT_SECRET_KEY must be configured")

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ADMIN_USERNAME = os.getenv("LEGACY_ADMIN_USERNAME", "")
ADMIN_PASSWORD_HASH = os.getenv("LEGACY_ADMIN_PASSWORD_HASH", "")


def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username, password):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
        return False
    return username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH)


def create_token():
    if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
        raise RuntimeError("Legacy administrator authentication is disabled")
    expire = datetime.utcnow() + timedelta(hours=8)
    return jwt.encode(
        {"sub": ADMIN_USERNAME, "role": "admin", "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
