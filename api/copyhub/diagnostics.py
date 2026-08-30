"""CopyHub v2 self-diagnostics.

This module deliberately uses deterministic, auditable reasoning rules for
trade-control safety. It can identify routing, connectivity and delivery
problems and perform only fail-closed remediations (pause/reroute). It never
opens, modifies or closes a MetaTrader position and it never resumes copying
without an explicit administrator action.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from api.copyhub.models import (
    CopyChannel,
    CopyDelivery,
    CopyDiagnosticIncident,
    CopyReceiver,
    PackageMasterRoute,
)
from api.mt5_ingest.models import ConnectorStatus, MasterTerminalRegistry
from api.onboarding.models import ClientOnboarding, SubscriptionPlan


MASTER_STALE_SECONDS = 150
RECEIVER_STALE_SECONDS = 120
DELIVERY_STALE_SECONDS = 180
FAILED_DELIVERY_WINDOW_MINUTES = 15
FAILED_DELIVERY_THRESHOLD = 3
ROUTABLE_PACKAGE_NAMES = {"starter", "standard", "professional", "enterprise"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fingerprint(code: str, entity_type: str, entity_id: str) -> str:
    raw = f"{code}|{entity_type}|{entity_id}".encode()
    return hashlib.sha256(raw).hexdigest()


def _record(
    db: Session,
    findings: list[dict],
    seen: set[str],
    *,
    code: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    detail: str,
    context: dict | None = None,
    auto_remediated: bool = False,
) -> None:
    fingerprint = _fingerprint(code, entity_type, entity_id)
    seen.add(fingerprint)
    row = db.query(CopyDiagnosticIncident).filter(
        CopyDiagnosticIncident.fingerprint == fingerprint
    ).first()
    now = utc_now()
    if row is None:
        row = CopyDiagnosticIncident(
            fingerprint=fingerprint,
            code=code,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            context=context or {},
            active=True,
            auto_remediated=auto_remediated,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(row)
    else:
        row.severity = severity
        row.detail = detail
        row.context = context or {}
        row.active = True
        row.auto_remediated = bool(row.auto_remediated or auto_remediated)
        row.last_seen_at = now
        row.resolved_at = None
    findings.append(
        {
            "code": code,
            "severity": severity,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "detail": detail,
            "context": context or {},
            "auto_remediated": auto_remediated,
        }
    )


def _channel_for_master(db: Session, account_number: str) -> CopyChannel | None:
    return db.query(CopyChannel).filter(
        CopyChannel.master_account == str(account_number)
    ).first()


def run_diagnostics(db: Session, *, auto_remediate: bool = True) -> dict:
    """Inspect copier internals and apply only safe fail-closed corrections."""

    now = utc_now()
    findings: list[dict] = []
    seen: set[str] = set()

    active_plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.active.is_(True)).all()
    plans = [
        plan for plan in active_plans
        if str(plan.name or "").strip().lower() in ROUTABLE_PACKAGE_NAMES
    ]
    routable_plan_ids = {plan.id for plan in plans}
    routes = db.query(PackageMasterRoute).filter(PackageMasterRoute.active.is_(True)).all()
    route_by_plan = {
        route.plan_id: route for route in routes
        if route.plan_id in routable_plan_ids
    }

    for plan in plans:
        route = route_by_plan.get(plan.id)
        if route is None:
            _record(
                db, findings, seen,
                code="PACKAGE_ROUTE_MISSING",
                severity="CRITICAL",
                entity_type="subscription_plan",
                entity_id=str(plan.id),
                detail=f"Active package {plan.name} has no master terminal route.",
                context={"plan_name": plan.name},
            )
            continue

        registry = db.query(MasterTerminalRegistry).filter(
            MasterTerminalRegistry.id == route.terminal_registry_id
        ).first()
        if registry is None or not registry.active:
            _record(
                db, findings, seen,
                code="PACKAGE_MASTER_UNAVAILABLE",
                severity="CRITICAL",
                entity_type="subscription_plan",
                entity_id=str(plan.id),
                detail=f"Package {plan.name} points to a missing or disabled master terminal.",
                context={"terminal_registry_id": route.terminal_registry_id},
            )
            continue

        if registry.subscriber_id is not None:
            _record(
                db, findings, seen,
                code="PACKAGE_ROUTE_NOT_OWNER_MASTER",
                severity="CRITICAL",
                entity_type="subscription_plan",
                entity_id=str(plan.id),
                detail=f"Package {plan.name} is mapped to a subscriber terminal instead of an owner/master terminal.",
                context={"terminal_registry_id": registry.id, "account_number": registry.account_number},
            )

        status = db.query(ConnectorStatus).filter(
            ConnectorStatus.connector_id == registry.connector_id
        ).first()
        age_seconds = None
        if status is not None and status.received_at is not None:
            age_seconds = max(0, int((now - status.received_at).total_seconds()))

        if status is None or age_seconds is None or age_seconds > MASTER_STALE_SECONDS:
            remediated = False
            channel = _channel_for_master(db, registry.account_number)
            if auto_remediate and channel is not None and not channel.globally_paused:
                channel.globally_paused = True
                remediated = True
            _record(
                db, findings, seen,
                code="MASTER_TELEMETRY_STALE",
                severity="CRITICAL",
                entity_type="master_terminal",
                entity_id=str(registry.id),
                detail=f"Master {registry.account_number} is not delivering fresh telemetry.",
                context={"plan_name": plan.name, "age_seconds": age_seconds},
                auto_remediated=remediated,
            )

    receivers = db.query(CopyReceiver).all()
    for receiver in receivers:
        onboarding = db.query(ClientOnboarding).filter(
            ClientOnboarding.subscriber_id == receiver.subscriber_id
        ).first()
        if onboarding is None or onboarding.plan_id is None:
            remediated = False
            if auto_remediate and (receiver.active or not receiver.paused):
                receiver.active = False
                receiver.paused = True
                remediated = True
            _record(
                db, findings, seen,
                code="RECEIVER_PACKAGE_MISSING",
                severity="CRITICAL",
                entity_type="receiver",
                entity_id=receiver.receiver_id,
                detail="Receiver has no active package selection and cannot be routed safely.",
                auto_remediated=remediated,
            )
            continue

        route = route_by_plan.get(onboarding.plan_id)
        registry = None
        if route is not None:
            registry = db.query(MasterTerminalRegistry).filter(
                MasterTerminalRegistry.id == route.terminal_registry_id,
                MasterTerminalRegistry.active.is_(True),
            ).first()

        if registry is None:
            remediated = False
            if auto_remediate and (receiver.active or not receiver.paused):
                receiver.active = False
                receiver.paused = True
                remediated = True
            _record(
                db, findings, seen,
                code="RECEIVER_ROUTE_UNAVAILABLE",
                severity="CRITICAL",
                entity_type="receiver",
                entity_id=receiver.receiver_id,
                detail="Receiver package does not currently resolve to an active master terminal.",
                context={"plan_id": onboarding.plan_id},
                auto_remediated=remediated,
            )
            continue

        expected_channel = _channel_for_master(db, registry.account_number)
        if expected_channel is not None and receiver.channel_id != expected_channel.id:
            remediated = False
            if auto_remediate:
                receiver.channel_id = expected_channel.id
                receiver.paused = True
                remediated = True
            _record(
                db, findings, seen,
                code="RECEIVER_ROUTE_MISMATCH",
                severity="CRITICAL",
                entity_type="receiver",
                entity_id=receiver.receiver_id,
                detail="Receiver was attached to a master that does not match its selected package.",
                context={"expected_master": registry.account_number},
                auto_remediated=remediated,
            )

        heartbeat_age = None
        if receiver.last_heartbeat_at is not None:
            heartbeat_age = max(0, int((now - receiver.last_heartbeat_at).total_seconds()))
        if receiver.active and (heartbeat_age is None or heartbeat_age > RECEIVER_STALE_SECONDS):
            remediated = False
            if auto_remediate and not receiver.paused:
                receiver.paused = True
                remediated = True
            _record(
                db, findings, seen,
                code="RECEIVER_HEARTBEAT_STALE",
                severity="HIGH",
                entity_type="receiver",
                entity_id=receiver.receiver_id,
                detail="Active receiver terminal heartbeat is stale.",
                context={"age_seconds": heartbeat_age},
                auto_remediated=remediated,
            )

        failed_since = now - timedelta(minutes=FAILED_DELIVERY_WINDOW_MINUTES)
        failed_count = db.query(CopyDelivery).filter(
            CopyDelivery.receiver_id == receiver.id,
            CopyDelivery.status.in_(["FAILED", "REJECTED"]),
            CopyDelivery.updated_at >= failed_since,
        ).count()
        if receiver.active and failed_count >= FAILED_DELIVERY_THRESHOLD:
            remediated = False
            if auto_remediate and not receiver.paused:
                receiver.paused = True
                remediated = True
            _record(
                db, findings, seen,
                code="REPEATED_DELIVERY_FAILURES",
                severity="CRITICAL",
                entity_type="receiver",
                entity_id=receiver.receiver_id,
                detail="Receiver has repeated recent delivery failures.",
                context={"failed_count": failed_count, "window_minutes": FAILED_DELIVERY_WINDOW_MINUTES},
                auto_remediated=remediated,
            )

        stale_pending = db.query(CopyDelivery).filter(
            CopyDelivery.receiver_id == receiver.id,
            CopyDelivery.status == "PENDING",
            CopyDelivery.created_at < now - timedelta(seconds=DELIVERY_STALE_SECONDS),
        ).count()
        if stale_pending:
            _record(
                db, findings, seen,
                code="STALE_PENDING_DELIVERIES",
                severity="HIGH",
                entity_type="receiver",
                entity_id=receiver.receiver_id,
                detail="Receiver has delivery records waiting longer than the expected acknowledgement window.",
                context={"count": stale_pending, "threshold_seconds": DELIVERY_STALE_SECONDS},
            )

    # Resolve incidents that disappeared during this diagnostic pass.
    for incident in db.query(CopyDiagnosticIncident).filter(
        CopyDiagnosticIncident.active.is_(True)
    ).all():
        if incident.fingerprint not in seen:
            incident.active = False
            incident.resolved_at = now
            incident.last_seen_at = now

    db.flush()
    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    highest = max((severity_rank.get(item["severity"], 0) for item in findings), default=0)
    health = "CRITICAL" if highest >= 4 else "DEGRADED" if highest >= 3 else "HEALTHY"
    return {
        "health": health,
        "finding_count": len(findings),
        "auto_remediation_enabled": auto_remediate,
        "findings": findings,
        "safety_model": "fail_closed_no_trade_mutation",
    }
