import hashlib
import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth.dependency import require_super_admin
from api.broker_accounts.models import BrokerAccount
from api.copyhub.models import CopyChannel, CopyDelivery, CopyEvent, CopyReceiver
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.mt5_ingest.models import ConnectorNonce
from api.mt5_ingest.routes import _verify as verify_connector_signature
from api.subscription_lifecycle.models import SubscriptionLifecycle


router = APIRouter(prefix="/copyhub/v1", tags=["Secure Copy Hub"])
MASTER_ACCOUNT = "49617874"


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def receiver_auth(db: Session, authorization: str | None, require_active: bool = True) -> CopyReceiver:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Receiver authentication required")
    supplied = authorization.split(" ", 1)[1]
    if len(supplied) < 48:
        raise HTTPException(401, "Invalid receiver credential")
    receiver = db.query(CopyReceiver).filter(CopyReceiver.token_hash == token_hash(supplied)).first()
    if receiver is None or (require_active and not receiver.active):
        raise HTTPException(403, "Receiver is not authorized")
    return receiver


class ProvisionReceiver(BaseModel):
    subscriber_id: int = Field(gt=0)
    broker_account_id: int = Field(gt=0)
    environment: str = Field(pattern="^(DEMO|LIVE)$")
    currency_unit: str = Field(pattern="^(USD|USC)$")
    is_cent_account: bool
    contract_size: float | None = Field(default=None, gt=0)
    min_lot: float | None = Field(default=None, gt=0)
    max_lot: float | None = Field(default=None, gt=0)
    lot_step: float | None = Field(default=None, gt=0)


class PauseRequest(BaseModel):
    paused: bool


class ActivationRequest(BaseModel):
    active: bool
    confirmation: str = Field(min_length=10, max_length=120)


class HeartbeatRequest(BaseModel):
    account_number: str = Field(min_length=5, max_length=32)
    environment: str = Field(pattern="^(DEMO|LIVE)$")
    currency_unit: str = Field(pattern="^(USD|USC)$")
    is_cent_account: bool
    contract_size: float = Field(gt=0)
    min_lot: float = Field(gt=0)
    max_lot: float = Field(gt=0)
    lot_step: float = Field(gt=0)


class DeliveryAck(BaseModel):
    status: str = Field(pattern="^(ACKNOWLEDGED|REJECTED|FAILED)$")
    receiver_ticket: str | None = Field(default=None, max_length=40)
    broker_code: str | None = Field(default=None, max_length=40)
    message: str | None = Field(default=None, max_length=500)


class MasterEvent(BaseModel):
    account_number: str = Field(min_length=5, max_length=32)
    event_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    master_ticket: str = Field(min_length=1, max_length=40)
    event_type: str = Field(pattern="^(OPEN|MODIFY|PARTIAL_CLOSE|CLOSE)$")
    symbol: str = Field(min_length=1, max_length=32)
    direction: str = Field(pattern="^(BUY|SELL)$")
    volume: float = Field(gt=0, allow_inf_nan=False)
    price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    stop_loss: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    take_profit: float | None = Field(default=None, ge=0, allow_inf_nan=False)


def get_or_create_channel(db: Session) -> CopyChannel:
    channel = db.query(CopyChannel).filter(CopyChannel.master_account == MASTER_ACCOUNT).first()
    if channel is None:
        channel = CopyChannel(name="Bethel Master", master_account=MASTER_ACCOUNT, globally_paused=True)
        db.add(channel)
        db.flush()
    return channel


@router.post("/master/events", status_code=202)
async def publish_master_event(request: Request, db: Session = Depends(get_db)):
    """Accept a signed master event and fan it out as non-executing delivery records."""
    body = await request.body()
    connector_id, nonce = verify_connector_signature(request, body)
    try:
        data = MasterEvent.model_validate(json.loads(body))
    except Exception:
        raise HTTPException(422, "Invalid master event")
    if data.account_number != MASTER_ACCOUNT:
        raise HTTPException(403, "Only the configured master account may publish")
    channel = get_or_create_channel(db)
    existing = db.query(CopyEvent).filter(CopyEvent.channel_id == channel.id, CopyEvent.event_key == data.event_key).first()
    digest = hashlib.sha256(body).hexdigest()
    if existing is not None:
        if existing.payload_hash != digest:
            raise HTTPException(409, "Event key was reused with different data")
        return {"status": "accepted", "idempotent": True, "event_id": existing.id}
    try:
        db.add(ConnectorNonce(connector_id=connector_id, nonce=nonce))
        event = CopyEvent(
            channel_id=channel.id, event_key=data.event_key,
            master_ticket=data.master_ticket, event_type=data.event_type,
            symbol=data.symbol.upper(), direction=data.direction, volume=data.volume,
            price=data.price, stop_loss=data.stop_loss, take_profit=data.take_profit,
            payload=data.model_dump(mode="json"), payload_hash=digest,
        )
        db.add(event)
        db.flush()
        receivers = db.query(CopyReceiver).filter(CopyReceiver.channel_id == channel.id, CopyReceiver.active.is_(True)).all()
        for receiver in receivers:
            db.add(CopyDelivery(receiver_id=receiver.id, event_id=event.id, status="PENDING"))
        db.commit()
        return {"status": "accepted", "idempotent": False, "event_id": event.id, "receiver_count": len(receivers)}
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Connector nonce or event was already used")
    except Exception:
        db.rollback()
        raise


@router.post("/admin/receivers", status_code=201)
def provision_receiver(data: ProvisionReceiver, db: Session = Depends(get_db), admin: dict = Depends(require_super_admin)):
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == data.subscriber_id).first()
    account = db.query(BrokerAccount).filter(BrokerAccount.id == data.broker_account_id).first()
    if subscriber is None or account is None or account.subscriber_id != data.subscriber_id:
        raise HTTPException(404, "Subscriber broker account not found")
    if account.login == MASTER_ACCOUNT:
        raise HTTPException(409, "Master account cannot be a receiver")
    if account.platform != "MT5":
        raise HTTPException(422, "The first receiver release supports MT5 only")
    expected_cent = data.currency_unit == "USC"
    if data.is_cent_account != expected_cent:
        raise HTTPException(422, "USC must be cent=true and USD must be cent=false")
    if data.environment == "LIVE" and not account.live_authorized:
        raise HTTPException(403, "Live broker account requires explicit authorization")
    raw_token = secrets.token_urlsafe(48)
    channel = get_or_create_channel(db)
    receiver = db.query(CopyReceiver).filter(CopyReceiver.broker_account_id == account.id).first()
    if receiver is None:
        receiver = CopyReceiver(
            receiver_id=f"mt5-{account.login}", channel_id=channel.id,
            subscriber_id=subscriber.id, broker_account_id=account.id,
            account_number=account.login, platform="MT5",
        )
        db.add(receiver)
    receiver.token_hash = token_hash(raw_token)
    receiver.environment = data.environment
    receiver.currency_unit = data.currency_unit
    receiver.is_cent_account = data.is_cent_account
    receiver.contract_size = data.contract_size
    receiver.min_lot = data.min_lot
    receiver.max_lot = data.max_lot
    receiver.lot_step = data.lot_step
    receiver.metadata_verified = all(v is not None for v in (data.contract_size, data.min_lot, data.max_lot, data.lot_step))
    receiver.live_authorized = bool(account.live_authorized and data.environment == "LIVE")
    receiver.active = False
    receiver.paused = True
    db.commit()
    return {"receiver_id": receiver.receiver_id, "receiver_token": raw_token, "token_shown_once": True, "active": False, "paused": True}


@router.patch("/admin/global-pause")
def global_pause(data: PauseRequest, db: Session = Depends(get_db), admin: dict = Depends(require_super_admin)):
    channel = get_or_create_channel(db)
    channel.globally_paused = data.paused
    db.commit()
    return {"master_account": MASTER_ACCOUNT, "globally_paused": channel.globally_paused}


@router.patch("/admin/receivers/{receiver_id}/pause")
def pause_receiver(receiver_id: str, data: PauseRequest, db: Session = Depends(get_db), admin: dict = Depends(require_super_admin)):
    receiver = db.query(CopyReceiver).filter(CopyReceiver.receiver_id == receiver_id).first()
    if receiver is None:
        raise HTTPException(404, "Receiver not found")
    receiver.paused = data.paused
    db.commit()
    return {"receiver_id": receiver.receiver_id, "paused": receiver.paused}


@router.patch("/admin/receivers/{receiver_id}/activation")
def activate_receiver(receiver_id: str, data: ActivationRequest, db: Session = Depends(get_db), admin: dict = Depends(require_super_admin)):
    receiver = db.query(CopyReceiver).filter(CopyReceiver.receiver_id == receiver_id).first()
    if receiver is None:
        raise HTTPException(404, "Receiver not found")
    expected = f"{'ACTIVATE' if data.active else 'DEACTIVATE'} RECEIVER {receiver.account_number}"
    if data.confirmation != expected:
        raise HTTPException(422, f"Confirmation must be: {expected}")
    if data.active:
        subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == receiver.subscriber_id).first()
        account = db.query(BrokerAccount).filter(BrokerAccount.id == receiver.broker_account_id).first()
        lifecycle = db.query(SubscriptionLifecycle).filter(SubscriptionLifecycle.subscriber_id == receiver.subscriber_id).first()
        if subscriber is None or subscriber.status != "ACTIVE":
            raise HTTPException(409, "Subscriber is not active")
        if account is None or account.status != "CONNECTED":
            raise HTTPException(409, "Broker account is not connected")
        if lifecycle is None or lifecycle.status not in {"ACTIVE", "GRACE"} or lifecycle.manual_suspended:
            raise HTTPException(409, "Subscription is not eligible for copying")
        if not receiver.metadata_verified or receiver.last_heartbeat_at is None:
            raise HTTPException(409, "Receiver terminal metadata and heartbeat must be verified")
        if receiver.environment == "LIVE" and not receiver.live_authorized:
            raise HTTPException(403, "Live execution has not been explicitly authorized")
    receiver.active = data.active
    receiver.paused = True
    db.commit()
    return {"receiver_id": receiver.receiver_id, "active": receiver.active, "paused": True}


@router.get("/admin/status")
def admin_status(db: Session = Depends(get_db), admin: dict = Depends(require_super_admin)):
    channel = get_or_create_channel(db)
    receivers = db.query(CopyReceiver).filter(CopyReceiver.channel_id == channel.id).all()
    db.commit()
    return {"master_account": channel.master_account, "active": channel.active, "globally_paused": channel.globally_paused, "receivers": [{"receiver_id": r.receiver_id, "account_number": r.account_number, "environment": r.environment, "currency_unit": r.currency_unit, "is_cent_account": r.is_cent_account, "metadata_verified": r.metadata_verified, "active": r.active, "paused": r.paused, "last_heartbeat_at": r.last_heartbeat_at} for r in receivers]}


@router.post("/receiver/heartbeat")
def heartbeat(data: HeartbeatRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    receiver = receiver_auth(db, authorization, require_active=False)
    if data.account_number != receiver.account_number or data.environment != receiver.environment:
        raise HTTPException(409, "Receiver terminal does not match its authorization")
    if data.currency_unit != receiver.currency_unit or data.is_cent_account != receiver.is_cent_account:
        raise HTTPException(409, "Receiver currency metadata mismatch")
    receiver.contract_size, receiver.min_lot, receiver.max_lot, receiver.lot_step = data.contract_size, data.min_lot, data.max_lot, data.lot_step
    receiver.metadata_verified = True
    receiver.last_heartbeat_at = utc_now()
    db.commit()
    return {"status": "online", "execution_enabled": False, "reason": "Receiver activation is a separate Super Admin step"}


@router.get("/receiver/events")
def receiver_events(limit: int = 100, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    receiver = receiver_auth(db, authorization)
    channel = db.query(CopyChannel).filter(CopyChannel.id == receiver.channel_id).first()
    lifecycle = db.query(SubscriptionLifecycle).filter(SubscriptionLifecycle.subscriber_id == receiver.subscriber_id).first()
    allowed = bool(channel and channel.active and not channel.globally_paused and not receiver.paused and receiver.metadata_verified and lifecycle and lifecycle.status in {"ACTIVE", "GRACE"} and not lifecycle.manual_suspended and (receiver.environment == "DEMO" or receiver.live_authorized))
    if not allowed:
        return {"execution_enabled": False, "events": []}
    rows = db.query(CopyDelivery, CopyEvent).join(CopyEvent, CopyEvent.id == CopyDelivery.event_id).filter(CopyDelivery.receiver_id == receiver.id, CopyDelivery.status == "PENDING").order_by(CopyEvent.id).limit(min(max(limit, 1), 250)).all()
    return {"execution_enabled": True, "events": [{"delivery_id": d.id, "event_key": e.event_key, "event_type": e.event_type, "master_ticket": e.master_ticket, "symbol": e.symbol, "direction": e.direction, "volume": e.volume, "price": e.price, "stop_loss": e.stop_loss, "take_profit": e.take_profit} for d, e in rows]}


@router.post("/receiver/deliveries/{delivery_id}/ack")
def acknowledge(delivery_id: int, data: DeliveryAck, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    receiver = receiver_auth(db, authorization)
    delivery = db.query(CopyDelivery).filter(CopyDelivery.id == delivery_id, CopyDelivery.receiver_id == receiver.id).first()
    if delivery is None:
        raise HTTPException(404, "Delivery not found")
    if delivery.status != "PENDING":
        return {"status": delivery.status, "idempotent": True}
    delivery.status = data.status
    delivery.receiver_ticket = data.receiver_ticket
    delivery.broker_code = data.broker_code
    delivery.message = data.message
    delivery.acknowledged_at = utc_now()
    db.commit()
    return {"status": delivery.status, "idempotent": False}
