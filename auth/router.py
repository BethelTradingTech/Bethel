"""
Bethel Trading Technologies
Authentication Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import SessionLocal
from auth.models import User
from auth.security import (
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)



def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()



@router.post("/register")
def register(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):

    existing_user = db.query(User).filter(
        User.email == email
    ).first()


    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


    user = User(
        email=email,
        hashed_password=hash_password(password)
    )


    db.add(user)

    db.commit()

    db.refresh(user)


    return {
        "message": "User created successfully",
        "user_id": user.id
    }



@router.post("/login")
def login(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == email
    ).first()


    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )


    if not verify_password(
        password,
        user.hashed_password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )


    token = create_access_token(
        {
            "sub": user.email
        }
    )


    return {

        "access_token": token,

        "token_type": "bearer"

    }