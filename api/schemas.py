from pydantic import BaseModel


class MT5ConnectionRequest(BaseModel):

    account_number: str
    server: str
    password: str