"""Render entry point with critical route isolation.

The main application keeps its existing startup behavior. This module ensures
critical connector, payment, notification, legal, profit-share, native KYC,
and private traffic-analytics routes remain available even when an unrelated
optional integration fails during main.py startup.
"""

import os

from fastapi import HTTPException

from main import app
from api.mt5_ingest.routes import router as mt5_ingest_router
from api.copyhub.live_activation_fix import router as live_activation_router
from api.payment_route_loader import mount_payment_routes
from api.database import Base as ApiBase, SessionLocal, engine as api_engine
from api.traffic.models import WebsiteTrafficEvent
from api.traffic.routes import router as traffic_router


SNAPSHOT_PATH = "/connector/v1/snapshot"
COPIER_ACTIVATION_PATH = "/copyhub/v1/receiver/activate"
TRAFFIC_VISIT_PATH = "/traffic/visit"
NOTIFICATIONS_PATH = "/admin/notifications"
LEGAL_DOCUMENTS_PATH = "/legal/documents"
PROFIT_SHARE_PATH = "/profit-share/{subscriber_id}"
NATIVE_KYC_READINESS_PATH = "/kyc/native/readiness"


def _route_exists(path: str) -> bool:
    return any(getattr(route, "path", None) == path for route in app.routes)


if not _route_exists(SNAPSHOT_PATH):
    app.include_router(mt5_ingest_router)
    print("MT5 Connector API Loaded (isolated Render entry point)")

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

# Native identity verification is mounted independently so an unrelated
# onboarding/payment integration cannot hide the KYC endpoints. Importing the
# models before create_all ensures the tables are registered on existing
# deployments without touching trading or subscriber tables.
try:
    from api.kyc import native_models as native_kyc_models
    from api.kyc.native_engine import readiness as native_kyc_readiness
    from api.kyc.native_routes import router as native_kyc_router

    ApiBase.metadata.create_all(bind=api_engine)
    if not _route_exists(NATIVE_KYC_READINESS_PATH):
        app.include_router(native_kyc_router)
        print("Bethel Native KYC API Loaded (isolated Render entry point)")
except Exception as error:
    native_kyc_readiness = None
    print("Bethel Native KYC isolated load error:", error)


@app.get("/ready")
def production_readiness():
    db = SessionLocal()
    try:
        native = native_kyc_readiness(db) if native_kyc_readiness else {"ready_for_native_cutover": False, "ready_for_native_identity": False, "error": "native_kyc_not_loaded"}
        selected = (os.getenv("IDENTITY_VERIFICATION_MODE") or "sumsub").strip().lower() == "native"
        if selected and not native.get("ready_for_native_cutover"):
            raise HTTPException(status_code=503, detail={"message": "Bethel Native KYC cutover selected but production readiness checks are incomplete", "native_kyc": native})
        return {
            "status": "ready",
            "identity_verification_provider": "bethel_native" if selected else "sumsub",
            "native_identity_verification": "ready_for_cutover" if native.get("ready_for_native_cutover") else "implemented_fail_closed",
            "native_kyc": native,
            "legacy_sumsub": {
                "selected": not selected,
                "mode": "disabled_by_native_cutover" if selected else "legacy_identity",
                "app_token_configured": bool((os.getenv("SUMSUB_APP_TOKEN") or "").strip()) if not selected else False,
                "level_configured": bool((os.getenv("SUMSUB_LEVEL_NAME") or "").strip()) if not selected else False,
                "webhook_verification": "disabled_by_native_cutover" if selected else bool((os.getenv("SUMSUB_WEBHOOK_SECRET") or "").strip()),
            },
        }
    finally:
        db.close()


WebsiteTrafficEvent.__table__.create(bind=api_engine, checkfirst=True)
if not _route_exists(TRAFFIC_VISIT_PATH):
    app.include_router(traffic_router)
    print("Bethel private website traffic analytics loaded")
