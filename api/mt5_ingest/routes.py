from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from api.database import SessionLocal
from api.auth.dependency import require_admin
from api.models import EquitySnapshot
from api.mt5_ingest.models import ConnectorNonce, ConnectorPosition, ConnectorStatus


router = APIRouter(prefix="/connector/v1", tags=["Read-only MT5 connector"])
MAX_CLOCK_SKEW_SECONDS = 300


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OpenPosition(BaseModel):
    ticket: str = Field(min_length=1, max_length=40)
    symbol: str = Field(min_length=1, max_length=32)
    direction: str = Field(pattern="^(BUY|SELL)$")
    volume: float = Field(gt=0, allow_inf_nan=False)
    open_price: float = Field(gt=0, allow_inf_nan=False)
    current_price: float = Field(gt=0, allow_inf_nan=False)
    stop_loss: float = Field(ge=0, allow_inf_nan=False, default=0)
    take_profit: float = Field(ge=0, allow_inf_nan=False, default=0)
    profit: float = Field(allow_inf_nan=False, default=0)
    swap: float = Field(allow_inf_nan=False, default=0)
    opened_at: datetime | None = None


class Snapshot(BaseModel):
    account_number: str = Field(min_length=5, max_length=32)
    server: str = Field(min_length=2, max_length=120)
    currency: str = Field(min_length=3, max_length=12)
    balance: float = Field(ge=0, allow_inf_nan=False)
    equity: float = Field(ge=0, allow_inf_nan=False)
    floating_profit: float = Field(allow_inf_nan=False)
    observed_at: datetime
    mode: str = Field(pattern="^(DEMO|LIVE)$")
    positions: list[OpenPosition] = Field(default_factory=list, max_length=1000)


def _verify(request: Request, body: bytes) -> tuple[str, str]:
    secret = os.getenv("MT5_CONNECTOR_SECRET", "")
    if len(secret) < 64:
        raise HTTPException(503, "Connector is not configured")
    connector_id = request.headers.get("x-bethel-connector-id", "")
    timestamp = request.headers.get("x-bethel-timestamp", "")
    nonce = request.headers.get("x-bethel-nonce", "")
    supplied = request.headers.get("x-bethel-signature", "")
    if not connector_id or not timestamp or not nonce or not supplied:
        raise HTTPException(401, "Signed connector request required")
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,100}", connector_id):
        raise HTTPException(401, "Invalid connector identifier")
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", nonce):
        raise HTTPException(401, "Invalid connector nonce")
    if not re.fullmatch(r"[a-f0-9]{64}", supplied):
        raise HTTPException(401, "Invalid connector signature")
    try:
        request_time = int(timestamp)
    except ValueError:
        raise HTTPException(401, "Invalid connector timestamp")
    if abs(int(time.time()) - request_time) > MAX_CLOCK_SKEW_SECONDS:
        raise HTTPException(401, "Expired connector request")
    message = timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(401, "Invalid connector signature")
    return connector_id, nonce


@router.post("/snapshot", status_code=202)
async def ingest_snapshot(request: Request):
    body = await request.body()
    connector_id, nonce = _verify(request, body)
    try:
        payload = Snapshot.model_validate(json.loads(body))
    except Exception:
        raise HTTPException(422, "Invalid snapshot payload")
    allowed = {value.strip() for value in os.getenv("MASTER_MT5_ACCOUNTS", "49617874").split(",") if value.strip()}
    if payload.account_number not in allowed:
        raise HTTPException(403, "Account is not an approved master account")
    configured_mode = os.getenv("MASTER_ACCOUNT_MODE", "DEMO").upper()
    if payload.mode != configured_mode:
        raise HTTPException(403, "Account mode does not match server configuration")
    now = datetime.now(timezone.utc)
    observed = payload.observed_at
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    if abs((now - observed.astimezone(timezone.utc)).total_seconds()) > 600:
        raise HTTPException(422, "Snapshot observation time is outside the allowed window")
    db = SessionLocal()
    try:
        db.query(ConnectorNonce).filter(
            ConnectorNonce.received_at < _utc_now_naive() - timedelta(days=1)
        ).delete(synchronize_session=False)
        db.add(ConnectorNonce(connector_id=connector_id, nonce=nonce))
        db.flush()
        db.add(EquitySnapshot(
            account_number=payload.account_number,
            balance=payload.balance,
            equity=payload.equity,
            profit=payload.floating_profit,
            timestamp=observed.astimezone(timezone.utc).replace(tzinfo=None),
        ))
        status = db.query(ConnectorStatus).filter(
            ConnectorStatus.connector_id == connector_id
        ).first()
        if status is None:
            status = ConnectorStatus(connector_id=connector_id)
            db.add(status)
        status.account_number = payload.account_number
        status.server = payload.server
        status.currency = payload.currency
        status.mode = payload.mode
        status.balance = payload.balance
        status.equity = payload.equity
        status.floating_profit = payload.floating_profit
        status.observed_at = observed.astimezone(timezone.utc).replace(tzinfo=None)
        status.received_at = _utc_now_naive()
        db.query(ConnectorPosition).filter(
            ConnectorPosition.connector_id == connector_id
        ).delete(synchronize_session=False)
        for position in payload.positions:
            opened_at = position.opened_at
            if opened_at is not None:
                if opened_at.tzinfo is None:
                    opened_at = opened_at.replace(tzinfo=timezone.utc)
                opened_at = opened_at.astimezone(timezone.utc).replace(tzinfo=None)
            db.add(ConnectorPosition(
                connector_id=connector_id,
                ticket=position.ticket,
                symbol=position.symbol,
                direction=position.direction,
                volume=position.volume,
                open_price=position.open_price,
                current_price=position.current_price,
                stop_loss=position.stop_loss,
                take_profit=position.take_profit,
                profit=position.profit,
                swap=position.swap,
                opened_at=opened_at,
                observed_at=observed.astimezone(timezone.utc).replace(tzinfo=None),
            ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Replay rejected")
    finally:
        db.close()
    return {"status": "accepted", "read_only": True}


@router.get("/status")
def connector_status(_admin=Depends(require_admin)):
    db = SessionLocal()
    try:
        statuses = db.query(ConnectorStatus).order_by(ConnectorStatus.received_at.desc()).all()
        now = _utc_now_naive()
        connectors = []
        for item in statuses:
            age_seconds = max(0, int((now - item.received_at).total_seconds()))
            positions = db.query(ConnectorPosition).filter(
                ConnectorPosition.connector_id == item.connector_id
            ).order_by(ConnectorPosition.symbol, ConnectorPosition.ticket).all()
            connectors.append({
                "connector_id": item.connector_id,
                "connection_status": "ONLINE" if age_seconds <= 150 else "STALE",
                "read_only": True,
                "last_seen": item.received_at.isoformat() + "Z",
                "age_seconds": age_seconds,
                "account_number": item.account_number,
                "server": item.server,
                "currency": item.currency,
                "account_mode": item.mode,
                "balance": round(float(item.balance), 2),
                "equity": round(float(item.equity), 2),
                "floating_profit": round(float(item.floating_profit), 2),
                "open_position_count": len(positions),
                "open_positions": [{
                    "ticket": position.ticket,
                    "symbol": position.symbol,
                    "direction": position.direction,
                    "volume": position.volume,
                    "open_price": position.open_price,
                    "current_price": position.current_price,
                    "stop_loss": position.stop_loss,
                    "take_profit": position.take_profit,
                    "profit": round(float(position.profit), 2),
                    "swap": round(float(position.swap), 2),
                    "opened_at": position.opened_at.isoformat() + "Z" if position.opened_at else None,
                } for position in positions],
            })
        return {"status": connectors[0]["connection_status"] if connectors else "OFFLINE", "read_only": True, "connectors": connectors}
    finally:
        db.close()
