from datetime import datetime, timedelta
from jose import jwt


SECRET_KEY = "BETHEL_TRADING_SECRET_CHANGE_LATER"

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