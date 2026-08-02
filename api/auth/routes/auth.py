"""
Bethel Trading Technologies
Authentication API Routes

Handles:
- Investor/Admin login
- Password verification
- JWT token generation
"""


from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.database import SessionLocal

from api.auth.models.user import User

from api.auth.services.security import verify_password

from api.auth.services.jwt import create_token



# ======================================
# AUTHENTICATION ROUTER
# ======================================


router = APIRouter(

    prefix="/auth",

    tags=["Authentication"]

)





class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


# ======================================
# LOGIN ENDPOINT
# ======================================


@router.post("/login")
def login(data: LoginRequest):


    db = SessionLocal()



    try:


        # Find user

        user = db.query(User).filter(

            User.email == str(data.email).strip().casefold()

        ).first()



        if not user:


            raise HTTPException(

                status_code=401,

                detail="Invalid credentials"

            )

        if not user.active:

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



        return {


            "status": "success",


            "message": "Login successful",


            "access_token": token,


            "token_type": "bearer",


            "user": {


                "id": user.id,

                "email": user.email,

                "role": user.role

            }


        }



    finally:


        db.close()
