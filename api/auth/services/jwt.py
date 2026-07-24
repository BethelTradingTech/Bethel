from datetime import datetime, timedelta
from jose import jwt


import os

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "development_secret_change_me"
)

ALGORITHM = "HS256"


def create_token(data):

    payload = data.copy()

    expire = datetime.utcnow() + timedelta(hours=24)

    payload["exp"] = expire

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_token(token):

    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )