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


import os
import secrets
import string

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from api.database import SessionLocal
from api.copytrading.models import CopySubscriber
from api.auth.rate_limit import check_registration_allowed

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
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)



class LoginRequest(BaseModel):

    email: str
    password: str




# ======================================
# CREATE PASSWORD
# ======================================


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_subscriber_password(data: RegisterRequest, request: Request):
    if os.getenv("PUBLIC_SUBSCRIBER_REGISTRATION_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=503, detail="Public registration is temporarily unavailable")
    check_registration_allowed(request)
    checks = (
        any(ch.islower() for ch in data.password),
        any(ch.isupper() for ch in data.password),
        any(ch.isdigit() for ch in data.password),
        any(ch in string.punctuation for ch in data.password),
    )
    if not all(checks):
        raise HTTPException(
            status_code=422,
            detail="Password must contain uppercase, lowercase, number, and special characters",
        )

    db = SessionLocal()
    try:
        email = str(data.email).strip().lower()
        existing = db.query(CopySubscriber).filter(func.lower(CopySubscriber.email) == email).first()
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        subscriber = CopySubscriber(
            name=data.name.strip(),
            email=email,
            password_hash=hash_password(data.password),
            mt5_account=f"PENDING-{secrets.token_hex(12)}",
            allocation_percent=100.0,
            status="PENDING",
            payment_status="UNPAID",
        )
        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)
        return {
            "status": "success",
            "subscriber_id": subscriber.id,
            "message": "Account created. Sign in to continue verification.",
        }
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Subscriber account already exists") from exc
    finally:
        db.close()


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
