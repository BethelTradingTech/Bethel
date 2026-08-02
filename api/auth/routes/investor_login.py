from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from api.auth.models.investor_user import InvestorUser
from api.auth.rate_limit import check_login_allowed, clear_login_failures, record_login_failure
from api.auth.services.jwt import create_token
from api.auth.services.security import verify_password
from api.database import SessionLocal


router = APIRouter(prefix="/investor/auth", tags=["Investor Authentication"])


class InvestorLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


@router.post("/login")
def login(
    data: InvestorLoginRequest,
    request: Request,
    response: Response,
):
    identifier = str(data.email).strip().casefold()
    check_login_allowed(request, identifier)
    db = SessionLocal()
    try:
        user = db.query(InvestorUser).filter(InvestorUser.email == identifier).first()
        if not user or not verify_password(data.password, user.password_hash):
            record_login_failure(request, identifier)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_token({
            "investor_id": user.investor_id,
            "role": "investor",
        })
        clear_login_failures(request, identifier)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=60 * 60,
            path="/",
        )
        return {
            "status": "success",
            "access_token": token,
            "token_type": "bearer",
        }
    finally:
        db.close()
