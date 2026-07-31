"""API schemas for multi-platform subscriber broker-account linking."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.broker_accounts.platforms import TradingPlatform, normalize_platform


class BrokerAccountLinkRequest(BaseModel):
    platform: TradingPlatform = TradingPlatform.MT5
    broker: str = Field(..., min_length=2, max_length=100)
    login: str = Field(..., min_length=1, max_length=100)
    server: str = Field(..., min_length=2, max_length=255)

    @field_validator("platform", mode="before")
    @classmethod
    def validate_platform(cls, value):
        return normalize_platform(value)

    @field_validator("broker", "login", "server")
    @classmethod
    def strip_values(cls, value):
        return str(value).strip()


class BrokerAccountCreate(BrokerAccountLinkRequest):
    subscriber_id: int


class LiveAccessRequest(BaseModel):
    enabled: bool
    confirmation: Literal["ENABLE LIVE MT5", "DISABLE LIVE MT5"]


class BrokerAccountResponse(BaseModel):
    id: int
    subscriber_id: int
    platform: str
    broker: str
    login: str
    server: str
    status: str
    connection_method: str
    execution_mode: str
    live_authorized: bool = False
    currency: Optional[str] = None
    leverage: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
