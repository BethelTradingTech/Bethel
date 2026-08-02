"""
Bethel Trading Technologies
Authentication API Routes

Handles:
- Investor/Admin login
- Password verification
- JWT token generation
"""


from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api.database import SessionLocal

from api.auth.models.user import User
from api.auth.models.super_admin_profile import SuperAdminProfile

from api.auth.services.security import verify_password

from api.auth.services.jwt import create_token
from api.auth.rate_limit import check_login_allowed, clear_login_failures, record_login_failure



# ======================================
# AUTHENTICATION ROUTER
# ======================================


router = APIRouter(

    prefix="/auth",

    tags=["Authentication"]

)





class LoginRequest(BaseModel):
    identifier: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12, max_length=256)


# ======================================
# LOGIN ENDPOINT
# ======================================


@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response):


    check_login_allowed(request, data.identifier)
    db = SessionLocal()



    try:


        # Find the real database-backed account by email or E.164 mobile.
        identifier = data.identifier.strip().casefold()
        profile = None
        if identifier.startswith("+"):
            normalized_mobile = "".join(
                char for char in identifier if char.isdigit() or char == "+"
            )
            profile = db.query(SuperAdminProfile).filter(
                SuperAdminProfile.mobile_number == normalized_mobile
            ).first()
            user = (
                db.query(User).filter(User.id == profile.user_id).first()
                if profile is not None
                else None
            )
        else:
            user = db.query(User).filter(User.email == identifier).first()
            if user is not None and user.role == "super_admin":
                profile = db.query(SuperAdminProfile).filter(
                    SuperAdminProfile.user_id == user.id
                ).first()



        if not user:

            record_login_failure(request, data.identifier)
            raise HTTPException(

                status_code=401,

                detail="Invalid credentials"

            )

        if not user.active:

            record_login_failure(request, data.identifier)
            raise HTTPException(

                status_code=403,

                detail="Account is disabled"

            )



        # Verify password

        password_valid = verify_password(

            data.password,

            user.password_hash

        )



        if not password_valid:

            record_login_failure(request, data.identifier)
            raise HTTPException(

                status_code=401,

                detail="Invalid credentials"

            )



        # Generate JWT token

        token = create_token(

            {

                "user_id": user.id,

                "role": user.role,

                "email": user.email

            }

        )



        clear_login_failures(request, data.identifier)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=8 * 60 * 60,
            path="/",
        )

        return {


            "status": "success",


            "message": "Login successful",


            "access_token": token,


            "token_type": "bearer",


            "user": {


                "id": user.id,

                "email": user.email,

                "role": user.role,
                "mobile_number": profile.mobile_number if profile else None,
                "mobile_verified": bool(profile.mobile_verified) if profile else False

            }


        }



    finally:


        db.close()
