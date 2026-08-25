"""
Bethel Trading Technologies
FastAPI Main Application

Institutional Quant Trading Platform
"""

import os

# ==========================
# FASTAPI CORE
# ==========================

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from api.broker_accounts import models as broker_account_models
from api.broker_accounts.routes import router as broker_accounts_router
from api.copytrading.onboarding_routes import router as onboarding_router

from api.copytrading.subscriber_routes import router as subscriber_router
from api.copytrading.dashboard_routes import router as copy_dashboard_router
from api.copytrading.order_routes import router as copy_order_router


# ==========================
# DATABASE
# ==========================

from api.database import engine
from api.models import Base
from api.traffic import models as traffic_models


# ==========================
# SERVICES
# ==========================

from api.services.scheduler import start_scheduler


# ==========================
# CORE ROUTES
# ==========================

from api.routes import accounts
from api.routes import dashboard
from api.routes import analytics
from api.routes import risk
from api.routes.investor import router as investor_mt5_status_router
from api.traffic.routes import router as traffic_router


# ==========================
# MT5 + PERFORMANCE ROUTES
# ==========================

from api.routes.mt5.router import router as mt5_router
from api.routes.performance.router import router as performance_router


# ==========================
# AUTHENTICATION ROUTES
# ==========================

from api.auth.routes.auth import router as auth_router
from api.auth.routes.investor_login import router as investor_auth_router


# ==========================
# INVESTOR SYSTEM ROUTES
# ==========================

from dashboard.investor_router import router as investor_router
from api.investors.routes.portfolio import router as portfolio_router
from api.copytrading.routes import router as copytrading_router
from api.investors.routes.mt5_accounts import router as mt5_accounts_router
from api.investors.routes.dashboard import router as investor_dashboard_router


# ==========================
# AUTH DEPENDENCY
# ==========================

from api.auth.dependency import check_auth


# ==========================
# CREATE APPLICATION
# ==========================

app = FastAPI(
    title="Bethel Trading Technologies API",
    description="Institutional Algorithmic Trading & Investor Portal",
    version="1.0"
)

PUBLIC_REGISTRATION_ENABLED = os.getenv(
    "PUBLIC_REGISTRATION_ENABLED",
    "false",
).strip().lower() == "true"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    # Funding-readiness / pre-launch gate: existing users and admin-created
    # subscribers continue to work, but unauthenticated public account creation
    # is closed unless deliberately re-enabled by configuration.
    if (
        request.method.upper() == "POST"
        and request.url.path.rstrip("/") == "/copytrading/auth/register"
        and not PUBLIC_REGISTRATION_ENABLED
    ):
        return JSONResponse(
            status_code=403,
            content={
                "detail": (
                    "Public registration is closed during Bethel's pre-launch "
                    "invitation-only phase. Request access through "
                    "info@betheltradingtechnologies.com."
                )
            },
            headers={"Cache-Control": "no-store"},
        )

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://static.sumsub.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://betheltradingtechnologies.com; "
        "connect-src 'self' https://api.betheltradingtechnologies.com https://bethel-api.onrender.com https://*.sumsub.com; "
        "frame-src https://*.sumsub.com; "
        "object-src 'none'; base-uri 'self'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


# ==========================
# DATABASE INITIALIZATION
# ==========================

Base.metadata.create_all(
    bind=engine
)


# ==========================
# START SERVICES
# ==========================

start_scheduler()


# ==========================
# CORS CONFIGURATION
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",

        "http://localhost:8081",
        "http://127.0.0.1:8081",

        # React PWA development server
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",

        # Production website
        "https://betheltradingtechnologies.com",
        "https://www.betheltradingtechnologies.com",

        # Cloudflare Pages
        "https://86207a4a.bethel-1vz.pages.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# STATIC FILES
# ==========================

app.mount(
    "/static",
    StaticFiles(
        directory="dashboard/static"
    ),
    name="static"
)

app.mount(
    "/admin-frontend",
    StaticFiles(directory="admin-frontend", html=True),
    name="admin-frontend",
)

app.mount(
    "/investor-frontend",
    StaticFiles(directory="investor-frontend", html=True),
    name="investor-frontend",
)


# ==========================
# TEMPLATE ENGINE
# ==========================

templates = Jinja2Templates(
    directory="dashboard/templates"
)


# ==========================
# API ROUTERS
# ==========================

app.include_router(accounts.router)
app.include_router(dashboard.router)
app.include_router(analytics.router)
app.include_router(risk.router)
app.include_router(investor_mt5_status_router)
app.include_router(mt5_router)
app.include_router(performance_router)
app.include_router(auth_router)
app.include_router(investor_auth_router)
app.include_router(portfolio_router)
app.include_router(mt5_accounts_router)
app.include_router(investor_router)
app.include_router(investor_dashboard_router)
app.include_router(copytrading_router)
app.include_router(subscriber_router)
app.include_router(copy_dashboard_router)
app.include_router(copy_order_router)
app.include_router(broker_accounts_router)
app.include_router(onboarding_router)
app.include_router(traffic_router)


# ==========================
# LOGIN PAGE
# ==========================

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


# ==========================
# HOME DASHBOARD
# ==========================

@app.get("/")
def dashboard_home(request: Request):
    auth = check_auth(request)

    if auth:
        return auth

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "company": "Bethel Trading Technologies"
        }
    )


# ==========================
# HEALTH CHECK
# ==========================

@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "Bethel Trading Technologies API",
        "version": "1.0"
    }