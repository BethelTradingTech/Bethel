"""
Bethel Trading Technologies
Authentication API Routes

Handles:
- Investor/Admin login
- Password verification
- JWT token generation
"""


from fastapi import APIRouter, HTTPException

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





# ======================================
# LOGIN ENDPOINT
# ======================================


@router.post("/login")
def login(

    email: str,

    password: str

):


    db = SessionLocal()



    try:


        # Find user

        user = db.query(User).filter(

            User.email == email

        ).first()



        if not user:


            raise HTTPException(

                status_code=401,

                detail="Invalid credentials"

            )



        # Verify password

        password_valid = verify_password(

            password,

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