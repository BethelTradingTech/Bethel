"""Render entry point with critical route isolation.

The main application keeps its existing startup behavior. This module ensures
critical connector and payment routes remain available even when an unrelated
optional integration fails during main.py startup.
"""

from main import app
from api.mt5_ingest.routes import router as mt5_ingest_router
from api.copyhub.live_activation_fix import router as live_activation_router
from api.payment_route_loader import mount_payment_routes


SNAPSHOT_PATH = "/connector/v1/snapshot"
COPIER_ACTIVATION_PATH = "/copyhub/v1/receiver/activate"

if not any(getattr(route, "path", None) == SNAPSHOT_PATH for route in app.routes):
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
