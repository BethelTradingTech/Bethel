"""Render entry point with critical route isolation.

The main application keeps its existing startup behavior. This module ensures
critical connector, payment, notification, legal, profit-share, native KYC,
and private traffic-analytics routes remain available even when an unrelated
optional integration fails during main.py startup.
"""

import os

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from main import app
from api.auth.dependency import require_admin
from api.mt5_ingest.routes import router as mt5_ingest_router
from api.broadcast.routes import router as broadcast_router
from api.copyhub.live_activation_fix import router as live_activation_router
from api.payment_route_loader import mount_payment_routes
from api.database import Base as ApiBase, SessionLocal, engine as api_engine
from api.public_assistant import router as public_assistant_router
from api.public_reviews import VisitorReview, router as public_reviews_router
from api.security_alerts import send_security_alert
from api.traffic.models import WebsiteTrafficEvent
from api.traffic.routes import router as traffic_router


SNAPSHOT_PATH = "/connector/v1/snapshot"
BROADCAST_WORKER_CONFIG_PATH = "/broadcast/v1/worker/config"
COPIER_ACTIVATION_PATH = "/copyhub/v1/receiver/activate"
TRAFFIC_VISIT_PATH = "/traffic/visit"
PUBLIC_ASSISTANT_PATH = "/public/assistant/chat"
PUBLIC_REVIEWS_PATH = "/public/reviews"
NOTIFICATIONS_PATH = "/admin/notifications"
LEGAL_DOCUMENTS_PATH = "/legal/documents"
PROFIT_SHARE_PATH = "/profit-share/{subscriber_id}"
NATIVE_KYC_READINESS_PATH = "/kyc/native/readiness"
NATIVE_KYC_ADMIN_REVIEW_PATH = "/admin/kyc/native/{subscriber_id}"
PROMO_ADMIN_PATH = "/admin/pricing/promos"


def _route_exists(path: str) -> bool:
    return any(getattr(route, "path", None) == path for route in app.routes)


def _ensure_promo_scope_columns() -> None:
    """Idempotently extend legacy promo tables without rewriting existing data."""
    inspector = inspect(api_engine)
    if "promo_codes" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("promo_codes")}
    statements = []
    if "scope" not in columns:
        statements.append("ALTER TABLE promo_codes ADD COLUMN scope VARCHAR(30) NOT NULL DEFAULT 'ANY_SUBSCRIPTION'")
    if "target_plan_id" not in columns:
        statements.append("ALTER TABLE promo_codes ADD COLUMN target_plan_id INTEGER")
    if not statements:
        return
    with api_engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    print("Promotion scope columns ready")


if not _route_exists(SNAPSHOT_PATH):
    app.include_router(mt5_ingest_router)
    print("MT5 Connector API Loaded (isolated Render entry point)")

if not _route_exists(BROADCAST_WORKER_CONFIG_PATH):
    app.include_router(broadcast_router)
    print("Broadcast API Loaded (isolated Render entry point)")

if not _route_exists(PUBLIC_ASSISTANT_PATH):
    app.include_router(public_assistant_router)
    print("Bethel public website assistant loaded")


VisitorReview.__table__.create(bind=api_engine, checkfirst=True)
if not _route_exists(PUBLIC_REVIEWS_PATH):
    app.include_router(public_reviews_router)
    print("Bethel moderated visitor reviews loaded")

app.router.routes[:] = [
    route
    for route in app.router.routes
    if not (
        getattr(route, "path", None) == COPIER_ACTIVATION_PATH
        and "POST" in (getattr(route, "methods", set()) or set())
    )
]
app.include_router(live_activation_router)
print("Bethel Copier terminal activation fix loaded")

mount_payment_routes(app)

try:
    from api.payment_admin.models import PromoCode, PromoRedemption

    PromoCode.__table__.create(bind=api_engine, checkfirst=True)
    PromoRedemption.__table__.create(bind=api_engine, checkfirst=True)
    _ensure_promo_scope_columns()
    from api.promo_admin_routes import router as promo_admin_router
    if not _route_exists(PROMO_ADMIN_PATH):
        app.include_router(promo_admin_router)
        print("Scoped Promotion Admin API Loaded")
except Exception as error:
    print("Scoped Promotion Admin API load error:", error)

try:
    from api.notifications.models import EmailDelivery
    from api.notifications.routes import router as email_notifications_router

    EmailDelivery.__table__.create(bind=api_engine, checkfirst=True)
    if not _route_exists(NOTIFICATIONS_PATH):
        app.include_router(email_notifications_router)
        print("Email Notifications API Loaded (isolated Render entry point)")
except Exception as error:
    print("Email Notifications isolated load error:", error)

try:
    from api.legal import models as legal_models
    from api.legal.routes import router as legal_consent_router

    if not _route_exists(LEGAL_DOCUMENTS_PATH):
        app.include_router(legal_consent_router)
        print("Legal API Loaded (isolated Render entry point)")
except Exception as error:
    print("Legal isolated load error:", error)

try:
    from api.profit_share import models as profit_share_models
    from api.profit_share.routes import router as profit_share_router

    if not _route_exists(PROFIT_SHARE_PATH):
        app.include_router(profit_share_router)
        print("Profit Share API Loaded (isolated Render entry point)")
except Exception as error:
    print("Profit Share isolated load error:", error)

try:
    from api.kyc import native_models as native_kyc_models
    from api.kyc.admin_review_routes import router as native_kyc_admin_review_router
    from api.kyc.native_engine import readiness as native_kyc_readiness
    from api.kyc.native_routes import router as native_kyc_router

    ApiBase.metadata.create_all(bind=api_engine)
    if not _route_exists(NATIVE_KYC_READINESS_PATH):
        app.include_router(native_kyc_router)
        print("Bethel Native KYC API Loaded (isolated Render entry point)")
    if not _route_exists(NATIVE_KYC_ADMIN_REVIEW_PATH):
        app.include_router(native_kyc_admin_review_router)
        print("Bethel Native KYC Compliance Review API Loaded")
except Exception as error:
    native_kyc_readiness = None
    print("Bethel Native KYC isolated load error:", error)


def _native_public_state(native: dict, selected: bool) -> dict:
    return {
        "provider": "bethel_native" if selected else "sumsub",
        "selected": selected,
        "available": bool(native.get("ready_for_native_identity")) if selected else True,
        "status": "available" if (not selected or native.get("ready_for_native_identity")) else "temporarily_unavailable",
    }


@app.middleware("http")
async def sanitize_native_kyc_readiness(request: Request, call_next):
    if request.url.path != NATIVE_KYC_READINESS_PATH:
        return await call_next(request)
    db = SessionLocal()
    try:
        native = native_kyc_readiness(db) if native_kyc_readiness else {}
        selected = (os.getenv("IDENTITY_VERIFICATION_MODE") or "sumsub").strip().lower() == "native"
        return JSONResponse(_native_public_state(native, selected), headers={"Cache-Control": "no-store"})
    finally:
        db.close()


@app.get("/admin/kyc/native/readiness")
def admin_native_kyc_readiness(_=Depends(require_admin)):
    db = SessionLocal()
    try:
        native = native_kyc_readiness(db) if native_kyc_readiness else {"ready_for_native_cutover": False, "ready_for_native_identity": False, "error": "native_kyc_not_loaded"}
        selected = (os.getenv("IDENTITY_VERIFICATION_MODE") or "sumsub").strip().lower() == "native"
        return {"provider": "bethel_native", "selected": selected, **native}
    finally:
        db.close()


@app.post("/admin/security/test-alert")
def admin_security_test_alert(_=Depends(require_admin)):
    sent = send_security_alert(
        event="Security notification test",
        severity="info",
        summary="Protected Bethel security-alert delivery test requested by an authenticated administrator.",
    )
    if not sent:
        raise HTTPException(
            status_code=503,
            detail="Security alert email was not sent. Verify SECURITY_ALERT_EMAIL/SMTP configuration.",
        )
    return {"status": "sent"}


@app.get("/ready")
def production_readiness():
    db = SessionLocal()
    try:
        native = native_kyc_readiness(db) if native_kyc_readiness else {"ready_for_native_cutover": False, "ready_for_native_identity": False, "error": "native_kyc_not_loaded"}
        selected = (os.getenv("IDENTITY_VERIFICATION_MODE") or "sumsub").strip().lower() == "native"
        if selected and not native.get("ready_for_native_cutover"):
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Bethel Native KYC cutover selected but production readiness checks are incomplete",
                    "identity_verification_provider": "bethel_native",
                    "native_identity_verification": "implemented_fail_closed",
                },
            )
        return {
            "status": "ready",
            "identity_verification_provider": "bethel_native" if selected else "sumsub",
            "native_identity_verification": "ready_for_cutover" if native.get("ready_for_native_cutover") else "implemented_fail_closed",
        }
    finally:
        db.close()


WebsiteTrafficEvent.__table__.create(bind=api_engine, checkfirst=True)
if not _route_exists(TRAFFIC_VISIT_PATH):
    app.include_router(traffic_router)
    print("Bethel private website traffic analytics loaded")
