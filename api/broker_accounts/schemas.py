"""
Bethel Trading Technologies

Broker Account Schemas

Purpose:
    API validation for subscriber MT5 account linking.
"""

from pydantic import BaseModel
from typing import Optional


class BrokerAccountCreate(BaseModel):

    subscriber_id: int

    broker: str = "MT5"

    login: str

    server: str



class BrokerAccountResponse(BaseModel):

    id: int

    subscriber_id: int

    broker: str

    login: str

    server: str

    status: str

    currency: Optional[str] = None

    leverage: Optional[int] = None


    class Config:
        from_attributes = True