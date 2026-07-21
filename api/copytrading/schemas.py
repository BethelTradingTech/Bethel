"""
Bethel Trading Technologies

Copy Trading Schemas

Purpose:
    Pydantic schemas for copy trading API communication.
"""


from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field



# ==========================================================
# CREATE COPY SUBSCRIBER
# ==========================================================

class SubscriberCreate(BaseModel):

    name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    email: str

    account_number: str

    allocation_percent: float = Field(
        default=100.0,
        gt=0,
        le=100
    )



# ==========================================================
# SUBSCRIBER RESPONSE
# ==========================================================

class SubscriberResponse(BaseModel):

    id: int

    name: str

    email: str

    mt5_account: str

    allocation_percent: float

    status: str

    created_at: datetime | None = None


    model_config = ConfigDict(
        from_attributes=True
    )



# ==========================================================
# MASTER TRADE CREATE REQUEST
# ==========================================================

class MasterTradeCreate(BaseModel):

    ticket: int

    symbol: str

    direction: str

    volume: float = Field(
        ...,
        gt=0
    )

    entry_price: float

    stop_loss: float | None = None

    take_profit: float | None = None



# ==========================================================
# COPY ORDER RESPONSE
# ==========================================================

class CopyOrderResponse(BaseModel):

    id: int

    subscriber_id: int

    master_ticket: int

    symbol: str

    direction: str

    volume: float

    status: str

    created_at: datetime | None = None


    model_config = ConfigDict(
        from_attributes=True
    )



# ==========================================================
# MASTER TRADE RESPONSE
# ==========================================================

class MasterTradeResponse(BaseModel):

    id: int

    ticket: int

    symbol: str

    direction: str

    volume: float

    entry_price: float

    status: str

    profit: float


    model_config = ConfigDict(
        from_attributes=True
    )