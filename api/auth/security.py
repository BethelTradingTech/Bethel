from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext


SECRET_KEY = "BETHEL_TRADING_SECRET_KEY_CHANGE_THIS"

ALGORITHM = "HS256"


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


ADMIN_USERNAME = "admin"


ADMIN_PASSWORD_HASH = pwd_context.hash(
    "Bethel@123"
)



def verify_password(
    plain_password,
    hashed_password
):

    return pwd_context.verify(
        plain_password,
        hashed_password
    )



def authenticate_user(
    username,
    password
):

    if username != ADMIN_USERNAME:
        return False


    if not verify_password(
        password,
        ADMIN_PASSWORD_HASH
    ):
        return False


    return True



def create_token():

    expire = datetime.utcnow() + timedelta(hours=8)


    token = jwt.encode(
        {
            "sub": ADMIN_USERNAME,
            "exp": expire
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )


    return token