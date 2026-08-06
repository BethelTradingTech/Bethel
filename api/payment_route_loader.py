"""Safely mount Bethel payment routers one gateway at a time.

A broken or unconfigured gateway must never prevent the API from starting.
"""

from importlib import import_module


def _has_route(app, path: str, method: str | None = None) -> bool:
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set()) or set()
        if method is None or method in methods:
            return True
    return False


def _mount(app, module_name: str, router_name: str, probe_path: str, method: str, label: str) -> None:
    if _has_route(app, probe_path, method):
        return
    try:
        module = import_module(module_name)
        router = getattr(module, router_name)
        app.include_router(router)
        print(f"{label} routes loaded")
    except Exception as exc:
        print(f"{label} routes unavailable: {exc}")


def mount_payment_routes(app) -> None:
    _mount(
        app,
        "api.stripe_payments.routes",
        "router",
        "/payments/stripe/{subscriber_id}/checkout",
        "POST",
        "Stripe",
    )
    _mount(
        app,
        "api.alternative_payments.routes",
        "router",
        "/payments/paypal/{subscriber_id}/order",
        "POST",
        "PayPal and Wise",
    )
    _mount(
        app,
        "api.payments.routes",
        "router",
        "/payments/binance/{subscriber_id}/order",
        "POST",
        "Binance Pay",
    )
    _mount(
        app,
        "api.payments.routes",
        "promo_router",
        "/payments/promos/{subscriber_id}/quote",
        "POST",
        "Promotion code",
    )
