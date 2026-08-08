"""
Bethel Trading Technologies

Main Platform Controller
FastAPI Application Entry Point
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from core.logger import get_logger
from database.database import database_status


logger = get_logger("BETHEL_SYSTEM")


# ======================================
# APPLICATION
# ======================================

app = FastAPI(
    title="Bethel Trading Technologies",
    description="Institutional Algorithmic Trading & Copy Trading Platform",
    version=settings.VERSION
)


# ======================================
# ADMIN FRONTEND
# ======================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


app.mount(
    "/admin-frontend",
    StaticFiles(
        directory=os.path.join(BASE_DIR, "admin-frontend"),
        html=True
    ),
    name="admin-frontend"
)

app.mount(
    "/investor-frontend",
    StaticFiles(
        directory=os.path.join(BASE_DIR, "investor-frontend"),
        html=True
    ),
    name="investor-frontend"
)

# ======================================
# CORS
# ======================================

PRODUCTION_MODE = (
    os.getenv("BETHEL_ENVIRONMENT", "DEVELOPMENT").upper() == "PRODUCTION"
)
PRODUCTION_ORIGINS = [
    "https://betheltradingtechnologies.com",
    "https://www.betheltradingtechnologies.com",
]
DEVELOPMENT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        PRODUCTION_ORIGINS
        if PRODUCTION_MODE
        else PRODUCTION_ORIGINS + DEVELOPMENT_ORIGINS
    ),
    allow_origin_regex=(
        None
        if PRODUCTION_MODE
        else r"^http://192\.168\.\d{1,3}\.\d{1,3}:517[3-6]$"
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Authorization",
        "Content-Type",
        "X-Requested-With",
    ],
    max_age=600,
)


# ======================================
# ROOT
# ======================================

@app.get("/")
def home():

    return {

        "system": "Bethel Trading Technologies",

        "status": "online",

        "version": settings.VERSION

    }



@app.get("/health")
def health():

    return {

        "status": "healthy",

        "database": database_status()

    }



# ======================================
# ROUTER LOADER HELPER
# ======================================

def load_router(

    module,

    name,

    prefix=None,

    tags=None

):

    try:

        router = module.router

        app.include_router(

            router,

            prefix=prefix,

            tags=tags

        )

        print(f"âœ“ {name} Loaded")


    except Exception as e:

        print(f"{name} Load Error:", e)



# ======================================
# AUTHENTICATION
# ======================================

from api.auth.routes.auth import router as auth_router


app.include_router(

    auth_router,

    tags=["Authentication"]

)


print("âœ“ Authentication API Loaded")



# ======================================
# SUBSCRIBER AUTHENTICATION
# ======================================

from api.copytrading.subscriber_auth_routes import router as subscriber_auth_router


app.include_router(

    subscriber_auth_router

)


print("âœ“ Subscriber Authentication API Loaded")



# ======================================
# COPY TRADING
# ======================================

try:

    from api.copytrading.routes import router as copy_router


    app.include_router(

        copy_router,

        prefix="/copytrading",

        tags=["Copy Trading"]

    )


    print("âœ“ Copy Trading API Loaded")


except Exception as e:

    print("Copy Trading Load Error:", e)



# ======================================
# SUBSCRIBER MANAGEMENT
# ======================================

try:

    from api.copytrading.subscriber_routes import router as subscriber_router


    app.include_router(

        subscriber_router,


        tags=["Copy Subscribers"]

    )


    print("âœ“ Subscriber API Loaded")


except Exception as e:

    print("Subscriber API Load Error:", e)


# ======================================
# COPY TRADING ORDERS
# ======================================

try:

    from api.copytrading.order_routes import router as order_router

    app.include_router(
        order_router,
        tags=["Copy Orders"]
    )

    print("âœ“ Copy Orders API Loaded")

except Exception as e:

    print("Copy Orders Load Error:", e)



# ======================================
# COPY TRADING DASHBOARD
# ======================================

try:

    from api.copytrading.dashboard_routes import router as dashboard_router

    app.include_router(
        dashboard_router,
        tags=["Copy Dashboard"]
    )

    print("âœ“ Copy Dashboard API Loaded")

except Exception as e:

    print("Copy Dashboard Load Error:", e)

# ======================================
# SUBSCRIBER ONBOARDING
# ======================================

try:

    from api.copytrading.onboarding_routes import router as onboarding_router


    app.include_router(

        onboarding_router

    )


    print("âœ“ Subscriber Onboarding Loaded")


except Exception as e:

    print("Onboarding Load Error:", e)


# ======================================
# BROKER ACCOUNTS
# ======================================

try:

    from api.broker_accounts.routes import router as broker_accounts_router

    app.include_router(

        broker_accounts_router

    )

    print("âœ“ Broker Accounts API Loaded")

except Exception as e:

    print("Broker Accounts API Load Error:", e)


# ======================================
# CLIENT ONBOARDING WORKFLOW
# ======================================

try:

    from api.onboarding.routes import router as client_onboarding_router
    from api.database import Base as ApiBase, engine as api_engine
    from api.broker_accounts.migrations import ensure_multiplatform_columns

    app.include_router(client_onboarding_router)

    from api.kyc.routes import router as kyc_router
    app.include_router(kyc_router)

    from api.payments import models as payment_models
    from api.payments.routes import router as payments_router
    app.include_router(payments_router)

    from api.subscriber_invites import models as subscriber_invite_models
    from api.subscriber_invites.routes import router as subscriber_invite_router
    app.include_router(subscriber_invite_router)

    from api.stripe_payments import models as stripe_payment_models
    from api.stripe_payments.routes import router as stripe_payment_router
    app.include_router(stripe_payment_router)

    from api.alternative_payments import models as alternative_payment_models
    from api.alternative_payments.routes import router as alternative_payment_router
    app.include_router(alternative_payment_router)

    from api.payment_admin import models as payment_admin_models
    from api.payment_admin.routes import router as payment_admin_router
    app.include_router(payment_admin_router)

    from api.subscription_lifecycle import models as subscription_lifecycle_models
    from api.subscription_lifecycle.routes import router as subscription_lifecycle_router
    app.include_router(subscription_lifecycle_router)

    from api.fund_management import models as fund_management_models
    from api.fund_management.routes import router as fund_management_router
    app.include_router(fund_management_router)

    from api.profit_share import models as profit_share_models
    from api.profit_share.routes import router as profit_share_router
    app.include_router(profit_share_router)

    from api.legal import models as legal_models
    from api.legal.routes import router as legal_consent_router
    app.include_router(legal_consent_router)

    from api.notifications import models as notification_models
    from api.notifications.routes import router as email_notifications_router
    app.include_router(email_notifications_router)

    from api.operations import models as operations_models
    from api.operations.audit import SecurityAuditMiddleware
    from api.operations.routes import router as operations_router
    app.include_router(operations_router)
    from api.mt5_ingest import models as mt5_ingest_models
    from api.mt5_ingest.routes import router as mt5_ingest_router
    app.include_router(mt5_ingest_router)
    from api.media.routes import router as media_router
    app.include_router(media_router)
    from api.copyhub import models as copyhub_models
    from api.copyhub.routes import router as copyhub_router
    app.include_router(copyhub_router)
    app.add_middleware(SecurityAuditMiddleware)

    from api.production_security import ProductionSecurityMiddleware
    app.add_middleware(ProductionSecurityMiddleware)

    from api.integrations.trust_remit import models as trust_remit_models
    from api.integrations.trust_remit.routes import router as trust_remit_router
    app.include_router(trust_remit_router)

    ApiBase.metadata.create_all(bind=api_engine)
    ensure_multiplatform_columns(api_engine)

    print("âœ“ Client Onboarding Workflow Loaded")

except Exception as e:

    print("Client Onboarding Workflow Load Error:", e)



# ======================================
# PERFORMANCE
# ======================================

try:

    from api.routes.performance.router import router as performance_router


    app.include_router(

        performance_router,

        prefix="",

        tags=["Performance"]

    )


    print("âœ“ Performance API Loaded")


except Exception as e:

    print("Performance API Load Error:", e)



# ======================================
# INVESTOR DASHBOARD
# ======================================

try:

    from api.routes.public_investor import router as investor_router
    from api.auth.routes.investor_login import router as investor_auth_router
    from api.investors.routes.dashboard import router as investor_dashboard_router
    from api.investors.routes.admin import router as admin_investors_router


    app.include_router(

        investor_router,

        tags=["Investor"]

    )

    app.include_router(investor_auth_router)
    app.include_router(investor_dashboard_router)
    app.include_router(admin_investors_router)


    print("âœ“ Investor API Loaded")


except Exception as e:

    print("Investor API Load Error:", e)

# Direct terminal status is available only on the Windows MT5 host. Keeping it
# separate ensures investor authentication and database dashboards still load
# in the Render Linux service.
try:
    from api.routes.investor import router as investor_status_router
    app.include_router(investor_status_router, tags=["Investor MT5 Local"])
except Exception as e:
    print("Local Investor MT5 Status Load Error:", e)



# ======================================
# DASHBOARD DATA API
# ======================================

try:
    from api.routes.dashboard import router as system_dashboard_router

    app.include_router(system_dashboard_router)

    print("Dashboard Data API Loaded")

except Exception as e:
    print("Dashboard Data API Load Error:", e)


# ======================================
# MT5
# ======================================

try:

    from api.routes.mt5.router import router as mt5_router

    app.include_router(
        mt5_router,
        tags=["MT5"]
    )


    print("âœ“ MT5 API Loaded")


except Exception as e:

    print("MT5 API Load Error:", e)




# ======================================
# ADMIN MANAGEMENT CONTROL
# ======================================

try:
    from api.admin.router import router as admin_control_router
    app.include_router(admin_control_router)
    print("âœ“ Admin Management Control Loaded")
except Exception as e:
    print("Admin Management Control Load Error:", e)

# ======================================
# STARTUP
# ======================================

@app.on_event("startup")
def startup_event():
    from api.database import SessionLocal
    from api.subscription_lifecycle.service import sweep_subscriptions
    from api.legal.service import seed_legal_documents
    from api.operations.backup import ensure_scheduled_backup
    from api.operations.scheduler import start_operations_scheduler
    startup_db = SessionLocal()
    try:
        seed_legal_documents(startup_db)
        sweep_subscriptions(startup_db)
        startup_db.commit()
    finally:
        startup_db.close()

    # Render Postgres provides managed backups. The in-process backup worker is
    # only for the legacy local SQLite installation.
    if os.getenv("DATABASE_URL", "").startswith("sqlite") or not os.getenv("DATABASE_URL"):
        ensure_scheduled_backup()
        start_operations_scheduler()

    print("=" * 40)

    print("BETHEL TRADING TECHNOLOGIES")

    print("QUANT PLATFORM")

    print("=" * 40)

    print()

    print(f"Version: {settings.VERSION}")

    print(f"Environment: {settings.ENVIRONMENT}")

    print()

    print("Modules:")

    print("âœ“ Configuration Loaded")

    print("âœ“ Logging Online")

    print(f"âœ“ {database_status()}")

    print()

    print("System Status: READY")

    print("=" * 40)



# ======================================
# RUN
# ======================================

if __name__ == "__main__":

    import uvicorn


    uvicorn.run(

        "main:app",

        host="127.0.0.1",

        port=8000,

        reload=False

    )
