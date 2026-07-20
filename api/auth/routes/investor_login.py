from fastapi import APIRouter, HTTPException, Response

from api.database import SessionLocal
from api.auth.models.investor_user import InvestorUser
from api.auth.services.security import verify_password
from api.auth.services.jwt import create_token


router = APIRouter(
    prefix="/investor/auth",
    tags=["Investor Authentication"]
)


@router.post("/login")
def login(
    response: Response,
    email: str,
    password: str
):

    db = SessionLocal()

    try:

        user = (
            db.query(InvestorUser)
            .filter(InvestorUser.email == email)
            .first()
        )

        if not user:

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if not verify_password(
            password,
            user.password_hash
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        token = create_token(
            {
                "investor_id": user.investor_id,
                "role": "investor"
            }
        )

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400,
            path="/"
        )

        return {
            "status": "success",
            "access_token": token,
            "token_type": "bearer"
        }

    finally:

        db.close()