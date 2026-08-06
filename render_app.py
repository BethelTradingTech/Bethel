"""Render entry point with critical route isolation.

The main application keeps its existing startup behavior. This module ensures
critical connector and payment routes remain mounted even if an unrelated
optional onboarding integration fails while main.py is importing.
"""

from main import app
from api.database import Base, engine
from api.mt5_ingest.routes import router as mt5_ingest_router
from api.copyhub.live_activation_fix import router as live_activation_router
from api.payments import models as payment_models
from api.payments.routes import router as binance_payment_router, promo_router
from api.stripe_payments import models as stripe_payment_models
from api.stripe_payments.routes import router as stripe_payment_router
from api.alternative_payments import models as alternative_payment_models
from api.alternative_payments.routes import router as alternative_payment_router


SNAPSHOT_PATH = "/connector/v1/snapshot"
COPIER_ACTIVATION_PATH = "/copyhub/v1/receiver/activate"


def has_route(path: str, method: str | None = None) -> bool:
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set()) or set()
        if method is None or method in methods:
            return True
    return False


if not has_route(SNAPSHOT_PATH):
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

# Payment routers used to live inside one large optional-import block in
# main.py. If any earlier optional module failed, every payment button returned
# 404 Not Found even though the gateway code existed. Mount each gateway here
# independently so Stripe, PayPal, Wise, Binance Pay, and promo routes remain
# available on the Render service.
if not has_route("/payments/stripe/{subscriber_id}/checkout", "POST"):
    app.include_router(stripe_payment_router)
    print("Stripe payment routes loaded")

if not has_route("/payments/paypal/{subscriber_id}/order", "POST"):
    app.include_router(alternative_payment_router)
    print("PayPal and Wise payment routes loaded")

if not has_route("/payments/binance/{subscriber_id}/order", "POST"):
    app.include_router(binance_payment_router)
    print("Binance Pay routes loaded")

if not has_route("/payments/promos/{subscriber_id}/quote", "POST"):
    app.include_router(promo_router)
    print("Promotion code routes loaded")

# Ensure any payment tables imported above exist in the production database.
Base.metadata.create_all(bind=engine)
