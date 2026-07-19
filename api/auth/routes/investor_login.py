from fastapi import APIRouter,HTTPException
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
    email:str,
    password:str
):

    db=SessionLocal()


    user=db.query(
        InvestorUser
    ).filter(
        InvestorUser.email==email
    ).first()


    if not user:

        raise HTTPException(
            401,
            "Invalid credentials"
        )


    if not verify_password(
        password,
        user.password_hash
    ):

        raise HTTPException(
            401,
            "Invalid credentials"
        )


    token=create_token(
        {
            "investor_id":user.investor_id,
            "role":"investor"
        }
    )


    return {

        "status":"success",

        "access_token":token,

        "token_type":"bearer"

    }