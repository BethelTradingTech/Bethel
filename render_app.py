"""Render entry point with critical route isolation.

The main application keeps its existing startup behavior. This module ensures
critical connector, payment, notification, legal, profit-share, and private
traffic-analytics routes remain available even when an unrelated optional
integration fails during main.py startup.
"""

from main import app
from api.mt5_ingest.routes import router as mt5_ingest_router
from api.copyhub.live_activation_fix import router as live_activation_router
from api.payment_route_loader import mount_payment_routes
from api.database import engine as api_engine
from api.traffic.models import WebsiteTrafficEvent
from api.traffic.routes import router as traffic_router


SNAPSHOT_PATH = "/connector/v1/snapshot"
COPIER_ACTIVATION_PATH = "/copyhub/v1/receiver/activate"
TRAFFIC_VISIT_PATH = "/traffic/visit"
NOTIFICATIONS_PATH = "/admin/notifications"
LEGAL_DOCUMENTS_PATH = "/legal/documents"
PROFIT_SHARE_PATH = "/profit-share/{subscriber_id}"


def _route_exists(path: str) -> bool:
    return any(getattr(route, "path", None) == path for route in app.routes)


if not _route_exists(SNAPSHOT_PATH):
    app.include_router(mt5_ingest_router)
    print("MT5 Connector API Loaded (isolated Render entry point)")

# Remove only the old POST activation endpoint. All other Copy Hub routes and
# controls remain unchanged. The replacement verifies LIVE or DEMO terminals
# while keeping the receiver inactive and paused until Super Admin approval.
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

# Each gateway is imported and mounted independently. A missing credential or
# broken optional gateway logs its own error without crashing the Render app or
# hiding the other payment routes.
mount_payment_routes(app)

# Keep admin email diagnostics available even if another onboarding module
# fails during main.py startup. This is required to expose SMTP delivery errors
# for password-reset and verification emails.
try:
    from api.notifications.models import EmailDelivery
    from api.notifications.routes import router as email_notifications_router

    EmailDelivery.__table__.create(bind=api_engine, checkfirst=True)
    if not _route_exists(NOTIFICATIONS_PATH):
        app.include_router(email_notifications_router)
        print("Email Notifications API Loaded (isolated Render entry point)")
except Exception as error:
    print("Email Notifications isolated load error:", error)

# Legal routes are isolated because the investor onboarding frontend depends on
# them independently of payment, KYC, or other optional modules.
try:
    from api.legal import models as legal_models
    from api.legal.routes import router as legal_consent_router

    if not _route_exists(LEGAL_DOCUMENTS_PATH):
        app.include_router(legal_consent_router)
        print("Legal API Loaded (isolated Render entry point)")
except Exception as error:
    print("Legal isolated load error:", error)

# Profit-share status is also used during onboarding and should not disappear
# because an unrelated module failed to import.
try:
    from api.profit_share import models as profit_share_models
    from api.profit_share.routes import router as profit_share_router

    if not _route_exists(PROFIT_SHARE_PATH):
        app.include_router(profit_share_router)
        print("Profit Share API Loaded (isolated Render entry point)")
except Exception as error:
    print("Profit Share isolated load error:", error)

# Website traffic analytics is isolated from trading and subscriber tables.
# The collector stores one-way visitor hashes, not raw IP addresses, and the
# reporting endpoint is protected by the existing Super Admin dependency.
WebsiteTrafficEvent.__table__.create(bind=api_engine, checkfirst=True)
if not _route_exists(TRAFFIC_VISIT_PATH):
    app.include_router(traffic_router)
    print("Bethel private website traffic analytics loaded")
