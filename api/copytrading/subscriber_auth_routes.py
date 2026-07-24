"""
Bethel Trading Technologies

Subscriber Authentication API

Handles:
- Subscriber password creation
- Subscriber login
- JWT token generation

Does NOT:
- Handle payments
- Execute trades
- Manage funds
"""


from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.database import SessionLocal
from api.copytrading.models import CopySubscriber

from api.security import (
    hash_password,
    verify_password,
    create_access_token
)



router = APIRouter(
    prefix="/copytrading/auth",
    tags=[
        "Subscriber Authentication"
    ]
)



# ======================================
# REQUEST MODELS
# ======================================


class RegisterRequest(BaseModel):

    email: str
    password: str



class LoginRequest(BaseModel):

    email: str
    password: str




# ======================================
# CREATE PASSWORD
# ======================================


@router.post("/register")
def register_subscriber(
    data: RegisterRequest
):

    db = SessionLocal()

    try:

        subscriber = (
            db.query(CopySubscriber)
            .filter(
                CopySubscriber.email == data.email
            )
            .first()
        )


        if not subscriber:

            raise HTTPException(
                status_code=404,
                detail="Subscriber not found"
            )



        subscriber.password_hash = hash_password(
            data.password
        )


        db.commit()



        return {

            "status": "success",

            "message":
            "Subscriber password created",

            "subscriber_id":
            subscriber.id

        }



    finally:

        db.close()




# ======================================
# LOGIN
# ======================================


@router.post("/login")
def subscriber_login(
    data: LoginRequest
):

    db = SessionLocal()

    try:

        subscriber = (
            db.query(CopySubscriber)
            .filter(
                CopySubscriber.email == data.email
            )
            .first()
        )


        if not subscriber:

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )



        if not subscriber.password_hash:

            raise HTTPException(
                status_code=400,
                detail="Password not created"
            )



        if not verify_password(
            data.password,
            subscriber.password_hash
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )



        token = create_access_token(
            {
                "subscriber_id":
                subscriber.id
            }
        )



        return {

            "status":
            "success",

            "access_token":
            token,

            "token_type":
            "bearer",

            "subscriber_id":
            subscriber.id,

            "name":
            subscriber.name

        }



    finally:

        db.close()