"""Package-controlled multi-master CopyHub v2.

Subscribers choose a subscription package, never a master terminal. The server
resolves the active package to an owner/master terminal and enforces that route
for provisioning, event fan-out and receiver polling.

The API is a control/distribution plane only. It never calls MetaTrader order
functions; execution remains inside the explicitly installed subscriber MT5
copier process.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth.dependency import require_super_admin
from api.broker_accounts.models import BrokerAccount
from api.copyhub.diagnostics import run_diagnostics
from api.copyhub.models import (
    CopyChannel,
    CopyDelivery,
    CopyEvent,
    CopyReceiver,
    PackageMasterRoute,
    ReceiverActivation,
)
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.mt5_ingest.models import ConnectorNonce, ConnectorStatus, MasterTerminalRegistry
from api.mt5_ingest.routes import _verify as verify_connector_signature
from api.onboarding.models import ClientOnboarding, SubscriptionPlan
from api.subscription_lifecycle.models import SubscriptionLifecycle


router = APIRouter(prefix="/copyhub/v2", tags=["Secure Package Copy Hub"])
MASTER_ONLINE_SECONDS = 150
RECEIVER_ONLINE_SECONDS = 120


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class PackageRouteRequest(BaseModel):
    terminal_registry_id: int = Field(gt=0)


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


class TerminalActivationRequest(BaseModel):
    activation_code: str = Field(min_length=20, max_length=120)
    account_number: str = Field(min_length=5, max_length=32)
    environment: str = Field(pattern="^(DEMO|LIVE)$")
    currency_unit: str = Field(pattern="^(USD|USC)$")
    is_cent_account: bool
    contract_size: float = Field(gt=0)
    min_lot: float = Field(gt=0)
    max_lot: float = Field(gt=0)
    lot_step: float = Field(gt=0)
    server: str | None = Field(default=None, min_length=2, max_length=255)
    leverage: int | None = Field(default=None, ge=0, le=10000)


class HeartbeatRequest(BaseModel):
    account_number: str = Field(min_length=5, max_length=32)
    environment: str = Field(pattern="^(DEMO|LIVE)$")
    currency_unit: str = Field(pattern="^(USD|USC)$")
    is_cent_account: bool
    contract_size: float = Field(gt=0)
    min_lot: float = Field(gt=0)
    max_lot: float = Field(gt=0)
    lot_step: float = Field(gt=0)
    server: str | None = Field(default=None, min_length=2, max_length=255)
    leverage: int | None = Field(default=None, ge=0, le=10000)


class PauseRequest(BaseModel):
    paused: bool


class ActivationRequest(BaseModel):
    active: bool
    confirmation: str = Field(min_length=10, max_length=120)


class DiagnosticsRequest(BaseModel):
    auto_remediate: bool = True


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


def _plan_for_subscriber(db: Session, subscriber_id: int) -> tuple[ClientOnboarding, SubscriptionPlan]:
    onboarding = db.query(ClientOnboarding).filter(
        ClientOnboarding.subscriber_id == subscriber_id
    ).first()
    if onboarding is None or onboarding.plan_id is None:
        raise HTTPException(409, "Subscriber must select a package before copier provisioning")
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == onboarding.plan_id,
        SubscriptionPlan.active.is_(True),
    ).first()
    if plan is None:
        raise HTTPException(409, "Subscriber package is unavailable")
    return onboarding, plan


def _registry_for_plan(db: Session, plan: SubscriptionPlan) -> tuple[PackageMasterRoute, MasterTerminalRegistry]:
    route = db.query(PackageMasterRoute).filter(
        PackageMasterRoute.plan_id == plan.id,
        PackageMasterRoute.active.is_(True),
    ).first()
    if route is None:
        raise HTTPException(409, f"{plan.name} has no active master route")
    registry = db.query(MasterTerminalRegistry).filter(
        MasterTerminalRegistry.id == route.terminal_registry_id,
        MasterTerminalRegistry.active.is_(True),
    ).first()
    if registry is None:
        raise HTTPException(409, f"{plan.name} master terminal is unavailable")
    if registry.subscriber_id is not None:
        raise HTTPException(409, "Package routing may use owner/master terminals only")
    return route, registry


def _channel_for_master(db: Session, account_number: str) -> CopyChannel:
    account_number = str(account_number).strip()
    channel = db.query(CopyChannel).filter(CopyChannel.master_account == account_number).first()
    if channel is None:
        base_name = f"Bethel Master {account_number}"
        name = base_name[:100]
        channel = CopyChannel(
            name=name,
            master_account=account_number,
            active=True,
            globally_paused=True,
        )
        db.add(channel)
        db.flush()
    return channel


def _expected_channel_for_subscriber(db: Session, subscriber_id: int) -> tuple[SubscriptionPlan, MasterTerminalRegistry, CopyChannel]:
    _, plan = _plan_for_subscriber(db, subscriber_id)
    _, registry = _registry_for_plan(db, plan)
    return plan, registry, _channel_for_master(db, registry.account_number)


def _master_status(db: Session, registry: MasterTerminalRegistry) -> tuple[ConnectorStatus | None, int | None]:
    status = db.query(ConnectorStatus).filter(
        ConnectorStatus.connector_id == registry.connector_id
    ).first()
    age = None
    if status is not None and status.received_at is not None:
        age = max(0, int((utc_now() - status.received_at).total_seconds()))
    return status, age


def _receiver_route_guard(db: Session, receiver: CopyReceiver, *, repair: bool) -> tuple[SubscriptionPlan, MasterTerminalRegistry, CopyChannel]:
    plan, registry, channel = _expected_channel_for_subscriber(db, receiver.subscriber_id)
    if receiver.channel_id != channel.id:
        if repair:
            receiver.channel_id = channel.id
            receiver.paused = True
            db.flush()
        else:
            raise HTTPException(409, "Receiver route no longer matches its subscription package")
    return plan, registry, channel


@router.get("/admin/package-routes")
def list_package_routes(db: Session = Depends(get_db), _admin=Depends(require_super_admin)):
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.id).all()
    rows = []
    for plan in plans:
        route = db.query(PackageMasterRoute).filter(PackageMasterRoute.plan_id == plan.id).first()
        registry = None
        status = None
        age = None
        if route is not None:
            registry = db.query(MasterTerminalRegistry).filter(
                MasterTerminalRegistry.id == route.terminal_registry_id
            ).first()
            if registry is not None:
                status, age = _master_status(db, registry)
        rows.append({
            "plan_id": plan.id,
            "plan_name": plan.name,
            "plan_active": plan.active,
            "route_active": bool(route and route.active),
            "terminal_registry_id": registry.id if registry else None,
            "master_account": registry.account_number if registry else None,
            "connector_id": registry.connector_id if registry else None,
            "master_mode": status.mode if status else None,
            "master_online": age is not None and age <= MASTER_ONLINE_SECONDS,
            "master_age_seconds": age,
        })
    return {"routes": rows, "subscriber_master_selection": False}


@router.put("/admin/package-routes/{plan_name}")
def set_package_route(
    plan_name: str,
    data: PackageRouteRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name).first()
    if plan is None:
        raise HTTPException(404, "Subscription package not found")
    registry = db.query(MasterTerminalRegistry).filter(
        MasterTerminalRegistry.id == data.terminal_registry_id,
        MasterTerminalRegistry.active.is_(True),
    ).first()
    if registry is None:
        raise HTTPException(404, "Active master terminal not found")
    if registry.subscriber_id is not None:
        raise HTTPException(409, "A subscriber terminal cannot be used as a package master")

    channel = _channel_for_master(db, registry.account_number)
    route = db.query(PackageMasterRoute).filter(PackageMasterRoute.plan_id == plan.id).first()
    old_registry_id = route.terminal_registry_id if route else None
    if route is None:
        route = PackageMasterRoute(plan_id=plan.id, terminal_registry_id=registry.id, active=True)
        db.add(route)
    else:
        route.terminal_registry_id = registry.id
        route.active = True

    migrated = 0
    if old_registry_id != registry.id:
        onboarding_rows = db.query(ClientOnboarding).filter(ClientOnboarding.plan_id == plan.id).all()
        subscriber_ids = [row.subscriber_id for row in onboarding_rows]
        if subscriber_ids:
            receivers = db.query(CopyReceiver).filter(CopyReceiver.subscriber_id.in_(subscriber_ids)).all()
            for receiver in receivers:
                if receiver.channel_id != channel.id:
                    receiver.channel_id = channel.id
                    # A route switch may occur while positions are open. Fail closed;
                    # an administrator must verify/resume the receiver explicitly.
                    receiver.paused = True
                    migrated += 1

    db.commit()
    return {
        "status": "mapped",
        "plan_name": plan.name,
        "master_account": registry.account_number,
        "terminal_registry_id": registry.id,
        "receivers_rerouted_and_paused": migrated,
        "subscriber_master_selection": False,
    }


@router.post("/admin/receivers", status_code=201)
def provision_receiver(
    data: ProvisionReceiver,
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == data.subscriber_id).first()
    account = db.query(BrokerAccount).filter(BrokerAccount.id == data.broker_account_id).first()
    if subscriber is None or account is None or account.subscriber_id != data.subscriber_id:
        raise HTTPException(404, "Subscriber broker account not found")
    plan, registry, channel = _expected_channel_for_subscriber(db, data.subscriber_id)
    if account.login == registry.account_number:
        raise HTTPException(409, "Master account cannot be a receiver")
    if account.platform != "MT5":
        raise HTTPException(422, "This copier release supports MT5 receivers only")
    expected_cent = data.currency_unit == "USC"
    if data.is_cent_account != expected_cent:
        raise HTTPException(422, "USC must be cent=true and USD must be cent=false")

    raw_token = secrets.token_urlsafe(48)
    activation_code = "BETHEL-" + secrets.token_urlsafe(24)
    receiver = db.query(CopyReceiver).filter(CopyReceiver.broker_account_id == account.id).first()
    if receiver is None:
        receiver = CopyReceiver(
            receiver_id=f"mt5-{account.login}",
            channel_id=channel.id,
            subscriber_id=subscriber.id,
            broker_account_id=account.id,
            account_number=account.login,
            platform="MT5",
        )
        db.add(receiver)
    else:
        receiver.channel_id = channel.id
    receiver.token_hash = token_hash(raw_token)
    receiver.environment = data.environment
    receiver.currency_unit = data.currency_unit
    receiver.is_cent_account = data.is_cent_account
    receiver.contract_size = data.contract_size
    receiver.min_lot = data.min_lot
    receiver.max_lot = data.max_lot
    receiver.lot_step = data.lot_step
    receiver.metadata_verified = all(v is not None for v in (data.contract_size, data.min_lot, data.max_lot, data.lot_step))
    receiver.live_authorized = False
    receiver.active = False
    receiver.paused = True
    db.flush()

    db.query(ReceiverActivation).filter(
        ReceiverActivation.receiver_id == receiver.id,
        ReceiverActivation.used_at.is_(None),
    ).delete(synchronize_session=False)
    db.add(ReceiverActivation(
        receiver_id=receiver.id,
        code_hash=token_hash(activation_code),
        expires_at=utc_now() + timedelta(hours=24),
    ))
    db.commit()
    return {
        "receiver_id": receiver.receiver_id,
        "activation_code": activation_code,
        "code_shown_once": True,
        "expires_in_hours": 24,
        "package": plan.name,
        "master_account": registry.account_number,
        "subscriber_master_selection": False,
        "active": False,
        "paused": True,
    }


@router.post("/receiver/activate")
def activate_terminal(data: TerminalActivationRequest, db: Session = Depends(get_db)):
    activation = db.query(ReceiverActivation).filter(
        ReceiverActivation.code_hash == token_hash(data.activation_code.strip()),
        ReceiverActivation.used_at.is_(None),
    ).first()
    if activation is None:
        raise HTTPException(401, "Invalid or already used activation code")
    activation.attempts += 1
    if activation.attempts > 5 or activation.expires_at < utc_now():
        db.commit()
        raise HTTPException(401, "Activation code has expired")

    receiver = db.query(CopyReceiver).filter(CopyReceiver.id == activation.receiver_id).first()
    if receiver is None or data.account_number != receiver.account_number:
        db.commit()
        raise HTTPException(409, "MT5 account does not match this activation")
    if data.currency_unit != receiver.currency_unit or data.is_cent_account != receiver.is_cent_account:
        db.commit()
        raise HTTPException(409, "MT5 USD/USC account type does not match this activation")

    plan, registry, channel = _receiver_route_guard(db, receiver, repair=True)
    receiver.environment = data.environment
    receiver.contract_size = data.contract_size
    receiver.min_lot = data.min_lot
    receiver.max_lot = data.max_lot
    receiver.lot_step = data.lot_step
    receiver.metadata_verified = True
    receiver.last_heartbeat_at = utc_now()
    receiver.active = False
    receiver.paused = True
    receiver.live_authorized = False
    receiver.channel_id = channel.id

    raw_token = secrets.token_urlsafe(48)
    receiver.token_hash = token_hash(raw_token)
    account = db.query(BrokerAccount).filter(BrokerAccount.id == receiver.broker_account_id).first()
    if account is not None:
        account.status = "CONNECTED"
        account.currency = data.currency_unit
        account.account_type = "CENT" if data.is_cent_account else "STANDARD"
        account.capital_verified = True
        account.last_verified_at = utc_now()
        if data.server:
            account.server = data.server
        if data.leverage is not None:
            account.leverage = data.leverage

    activation.used_at = utc_now()
    db.commit()
    return {
        "status": "activated",
        "receiver_id": receiver.receiver_id,
        "receiver_token": raw_token,
        "token_shown_once": True,
        "package": plan.name,
        "master_account": registry.account_number,
        "active": False,
        "paused": True,
        "terminal_verified": True,
        "live_authorization_required": receiver.environment == "LIVE",
    }


@router.post("/receiver/heartbeat")
def heartbeat(
    data: HeartbeatRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    receiver = receiver_auth(db, authorization, require_active=False)
    if data.account_number != receiver.account_number or data.environment != receiver.environment:
        raise HTTPException(409, "Receiver terminal does not match its authorization")
    if data.currency_unit != receiver.currency_unit or data.is_cent_account != receiver.is_cent_account:
        raise HTTPException(409, "Receiver currency metadata mismatch")
    plan, registry, channel = _receiver_route_guard(db, receiver, repair=True)
    receiver.contract_size = data.contract_size
    receiver.min_lot = data.min_lot
    receiver.max_lot = data.max_lot
    receiver.lot_step = data.lot_step
    receiver.metadata_verified = True
    receiver.last_heartbeat_at = utc_now()
    db.commit()
    return {
        "status": "online",
        "package": plan.name,
        "master_account": registry.account_number,
        "route_locked_to_package": True,
        "active": receiver.active,
        "paused": receiver.paused,
    }


@router.patch("/admin/receivers/{receiver_id}/activation")
def set_receiver_activation(
    receiver_id: str,
    data: ActivationRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    receiver = db.query(CopyReceiver).filter(CopyReceiver.receiver_id == receiver_id).first()
    if receiver is None:
        raise HTTPException(404, "Receiver not found")
    expected = f"{'ACTIVATE' if data.active else 'DEACTIVATE'} RECEIVER {receiver.account_number}"
    if data.confirmation != expected:
        raise HTTPException(422, f"Confirmation must be: {expected}")

    plan, registry, channel = _receiver_route_guard(db, receiver, repair=True)
    if data.active:
        subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == receiver.subscriber_id).first()
        account = db.query(BrokerAccount).filter(BrokerAccount.id == receiver.broker_account_id).first()
        lifecycle = db.query(SubscriptionLifecycle).filter(
            SubscriptionLifecycle.subscriber_id == receiver.subscriber_id
        ).first()
        status, age = _master_status(db, registry)
        if subscriber is None or subscriber.status != "ACTIVE":
            raise HTTPException(409, "Subscriber is not active")
        if account is None or account.status != "CONNECTED":
            raise HTTPException(409, "Broker account is not connected")
        if lifecycle is None or lifecycle.status not in {"ACTIVE", "GRACE"} or lifecycle.manual_suspended:
            raise HTTPException(409, "Subscription is not eligible for copying")
        if not receiver.metadata_verified or receiver.last_heartbeat_at is None:
            raise HTTPException(409, "Receiver terminal metadata and heartbeat must be verified")
        if status is None or age is None or age > MASTER_ONLINE_SECONDS:
            raise HTTPException(409, "Package master terminal is offline or stale")
        if receiver.environment == "LIVE":
            if status.mode != "LIVE":
                raise HTTPException(409, "A LIVE receiver cannot be activated against a DEMO package master")
            if not account.live_authorized:
                raise HTTPException(403, "Live broker account has not been explicitly authorized")
            receiver.live_authorized = True
        else:
            receiver.live_authorized = False
        receiver.channel_id = channel.id
    receiver.active = data.active
    receiver.paused = True
    db.commit()
    return {
        "receiver_id": receiver.receiver_id,
        "package": plan.name,
        "master_account": registry.account_number,
        "active": receiver.active,
        "paused": True,
    }


@router.patch("/admin/receivers/{receiver_id}/pause")
def pause_receiver(
    receiver_id: str,
    data: PauseRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    receiver = db.query(CopyReceiver).filter(CopyReceiver.receiver_id == receiver_id).first()
    if receiver is None:
        raise HTTPException(404, "Receiver not found")
    plan, registry, channel = _receiver_route_guard(db, receiver, repair=True)
    if not data.paused:
        if not receiver.active:
            raise HTTPException(409, "Receiver must be active before copying can resume")
        status, age = _master_status(db, registry)
        if status is None or age is None or age > MASTER_ONLINE_SECONDS:
            raise HTTPException(409, "Package master terminal is not healthy enough to resume")
        if channel.globally_paused:
            raise HTTPException(409, "Package master channel is globally paused")
    receiver.paused = data.paused
    db.commit()
    return {
        "receiver_id": receiver.receiver_id,
        "package": plan.name,
        "master_account": registry.account_number,
        "paused": receiver.paused,
    }


@router.patch("/admin/package-routes/{plan_name}/pause")
def pause_package_channel(
    plan_name: str,
    data: PauseRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name).first()
    if plan is None:
        raise HTTPException(404, "Subscription package not found")
    _, registry = _registry_for_plan(db, plan)
    channel = _channel_for_master(db, registry.account_number)
    if not data.paused:
        status, age = _master_status(db, registry)
        if status is None or age is None or age > MASTER_ONLINE_SECONDS:
            raise HTTPException(409, "Master terminal must be online before package copying can resume")
    channel.globally_paused = data.paused
    db.commit()
    return {"plan_name": plan.name, "master_account": registry.account_number, "globally_paused": channel.globally_paused}


@router.post("/master/events", status_code=202)
async def publish_master_event(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    connector_id, nonce = verify_connector_signature(request, body)
    try:
        data = MasterEvent.model_validate(json.loads(body))
    except Exception:
        raise HTTPException(422, "Invalid master event")

    registry = db.query(MasterTerminalRegistry).filter(
        MasterTerminalRegistry.connector_id == connector_id,
        MasterTerminalRegistry.account_number == data.account_number,
        MasterTerminalRegistry.active.is_(True),
        MasterTerminalRegistry.subscriber_id.is_(None),
    ).first()
    if registry is None:
        raise HTTPException(403, "Master event connector is not registered for this owner/master account")
    route_count = db.query(PackageMasterRoute).filter(
        PackageMasterRoute.terminal_registry_id == registry.id,
        PackageMasterRoute.active.is_(True),
    ).count()
    if route_count == 0:
        raise HTTPException(409, "Master account is not assigned to any active subscription package")

    channel = _channel_for_master(db, data.account_number)
    if not channel.active or channel.globally_paused:
        raise HTTPException(423, "Master copy channel is paused")
    status, age = _master_status(db, registry)
    if status is None or age is None or age > MASTER_ONLINE_SECONDS:
        channel.globally_paused = True
        db.commit()
        raise HTTPException(423, "Master telemetry is stale; channel paused automatically")

    digest = hashlib.sha256(body).hexdigest()
    existing = db.query(CopyEvent).filter(
        CopyEvent.channel_id == channel.id,
        CopyEvent.event_key == data.event_key,
    ).first()
    if existing is not None:
        if existing.payload_hash != digest:
            raise HTTPException(409, "Event key was reused with different data")
        return {"status": "accepted", "idempotent": True, "event_id": existing.id}

    try:
        db.add(ConnectorNonce(connector_id=connector_id, nonce=nonce))
        event = CopyEvent(
            channel_id=channel.id,
            event_key=data.event_key,
            master_ticket=data.master_ticket,
            event_type=data.event_type,
            symbol=data.symbol.upper(),
            direction=data.direction,
            volume=data.volume,
            price=data.price,
            stop_loss=data.stop_loss,
            take_profit=data.take_profit,
            payload=data.model_dump(mode="json"),
            payload_hash=digest,
        )
        db.add(event)
        db.flush()

        delivered = 0
        receivers = db.query(CopyReceiver).filter(
            CopyReceiver.active.is_(True),
            CopyReceiver.paused.is_(False),
        ).all()
        for receiver in receivers:
            try:
                _, expected_registry, expected_channel = _receiver_route_guard(db, receiver, repair=True)
            except HTTPException:
                receiver.paused = True
                continue
            if expected_registry.id != registry.id or expected_channel.id != channel.id:
                continue
            db.add(CopyDelivery(receiver_id=receiver.id, event_id=event.id, status="PENDING"))
            delivered += 1
        db.commit()
        return {
            "status": "accepted",
            "idempotent": False,
            "event_id": event.id,
            "receiver_count": delivered,
            "master_account": data.account_number,
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Connector nonce or event was already used")


@router.get("/receiver/events")
def receiver_events(
    limit: int = 100,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    receiver = receiver_auth(db, authorization)
    plan, registry, channel = _receiver_route_guard(db, receiver, repair=True)
    lifecycle = db.query(SubscriptionLifecycle).filter(
        SubscriptionLifecycle.subscriber_id == receiver.subscriber_id
    ).first()
    status, master_age = _master_status(db, registry)
    receiver_age = None
    if receiver.last_heartbeat_at is not None:
        receiver_age = max(0, int((utc_now() - receiver.last_heartbeat_at).total_seconds()))

    allowed = bool(
        channel.active
        and not channel.globally_paused
        and not receiver.paused
        and receiver.metadata_verified
        and receiver_age is not None
        and receiver_age <= RECEIVER_ONLINE_SECONDS
        and status is not None
        and master_age is not None
        and master_age <= MASTER_ONLINE_SECONDS
        and lifecycle
        and lifecycle.status in {"ACTIVE", "GRACE"}
        and not lifecycle.manual_suspended
        and (receiver.environment == "DEMO" or receiver.live_authorized)
    )
    if not allowed:
        db.commit()
        return {
            "execution_enabled": False,
            "events": [],
            "package": plan.name,
            "master_account": registry.account_number,
            "route_locked_to_package": True,
        }

    rows = db.query(CopyDelivery, CopyEvent).join(
        CopyEvent, CopyEvent.id == CopyDelivery.event_id
    ).filter(
        CopyDelivery.receiver_id == receiver.id,
        CopyDelivery.status == "PENDING",
    ).order_by(CopyEvent.id).limit(min(max(limit, 1), 250)).all()
    now = utc_now()
    events = []
    for delivery, event in rows:
        delivery.attempts += 1
        delivery.delivered_at = now
        events.append({
            "delivery_id": delivery.id,
            "event_key": event.event_key,
            "event_type": event.event_type,
            "master_ticket": event.master_ticket,
            "symbol": event.symbol,
            "direction": event.direction,
            "volume": event.volume,
            "price": event.price,
            "stop_loss": event.stop_loss,
            "take_profit": event.take_profit,
        })
    db.commit()
    return {
        "execution_enabled": True,
        "events": events,
        "package": plan.name,
        "master_account": registry.account_number,
        "route_locked_to_package": True,
    }


@router.post("/receiver/deliveries/{delivery_id}/ack")
def acknowledge(
    delivery_id: int,
    data: DeliveryAck,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    receiver = receiver_auth(db, authorization)
    _receiver_route_guard(db, receiver, repair=True)
    delivery = db.query(CopyDelivery).filter(
        CopyDelivery.id == delivery_id,
        CopyDelivery.receiver_id == receiver.id,
    ).first()
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


@router.post("/admin/diagnostics/run")
def diagnostics(
    data: DiagnosticsRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    result = run_diagnostics(db, auto_remediate=data.auto_remediate)
    db.commit()
    return result


@router.get("/admin/status")
def admin_status(db: Session = Depends(get_db), _admin=Depends(require_super_admin)):
    health = run_diagnostics(db, auto_remediate=False)
    receivers = db.query(CopyReceiver).all()
    rows = []
    for receiver in receivers:
        plan_name = None
        master_account = None
        route_ok = False
        try:
            plan, registry, channel = _receiver_route_guard(db, receiver, repair=False)
            plan_name = plan.name
            master_account = registry.account_number
            route_ok = receiver.channel_id == channel.id
        except HTTPException:
            pass
        heartbeat_age = None
        if receiver.last_heartbeat_at is not None:
            heartbeat_age = max(0, int((utc_now() - receiver.last_heartbeat_at).total_seconds()))
        rows.append({
            "receiver_id": receiver.receiver_id,
            "account_number": receiver.account_number,
            "package": plan_name,
            "master_account": master_account,
            "route_ok": route_ok,
            "active": receiver.active,
            "paused": receiver.paused,
            "environment": receiver.environment,
            "metadata_verified": receiver.metadata_verified,
            "heartbeat_age_seconds": heartbeat_age,
            "online": heartbeat_age is not None and heartbeat_age <= RECEIVER_ONLINE_SECONDS,
        })
    db.commit()
    return {
        "health": health,
        "receiver_count": len(rows),
        "receivers": rows,
        "subscriber_master_selection": False,
        "routing_mode": "subscription_package_enforced",
    }
