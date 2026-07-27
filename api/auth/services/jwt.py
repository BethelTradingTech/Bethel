from datetime import datetime, timedelta
import os

from jose import jwt


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if len(SECRET_KEY) < 64:
    raise RuntimeError("JWT_SECRET_KEY must be configured with at least 64 characters")

ALGORITHM = "HS256"
ACCESS_TOKEN_HOURS = int(os.getenv("ADMIN_TOKEN_EXPIRE_HOURS", "8"))


def create_token(data):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
