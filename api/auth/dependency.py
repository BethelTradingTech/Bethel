from fastapi import Request
from fastapi.responses import RedirectResponse

from api.auth.security import SECRET_KEY, ALGORITHM

from jose import jwt, JWTError



def check_auth(request: Request):


    token = request.cookies.get(
        "access_token"
    )


    if not token:


        authorization = request.headers.get(
            "Authorization"
        )


        if authorization and authorization.startswith(
            "Bearer "
        ):


            token = authorization.split(
                " "
            )[1]



    if not token:

        return RedirectResponse(
            "/login"
        )



    try:

        jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[
                ALGORITHM
            ]
        )


    except JWTError:

        return RedirectResponse(
            "/login"
        )


    return None