from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from api.auth.security import (
    authenticate_user,
    create_token
)


router = APIRouter()



@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...)
):

    if authenticate_user(
        username,
        password
    ):

        response = RedirectResponse(
            "/",
            status_code=302
        )


        response.set_cookie(
            key="access_token",
            value=create_token()
        )


        return response


    return {
        "error":"Invalid login"
    }