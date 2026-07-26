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

app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://localhost:5175",
        "http://127.0.0.1:5175",

        "http://localhost:5174",
        "http://127.0.0.1:5174",

        "http://localhost:5173",
        "http://127.0.0.1:5173",

        "http://localhost:8080",
        "http://127.0.0.1:8080",

        "http://localhost:8081",
        "http://127.0.0.1:8081",

        "https://betheltradingtechnologies.com",

        "https://www.betheltradingtechnologies.com",

    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

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

        print(f"✓ {name} Loaded")


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


print("✓ Authentication API Loaded")



# ======================================
# SUBSCRIBER AUTHENTICATION
# ======================================

from api.copytrading.subscriber_auth_routes import router as subscriber_auth_router


app.include_router(

    subscriber_auth_router

)


print("✓ Subscriber Authentication API Loaded")



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


    print("✓ Copy Trading API Loaded")


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


    print("✓ Subscriber API Loaded")


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

    print("✓ Copy Orders API Loaded")

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

    print("✓ Copy Dashboard API Loaded")

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


    print("✓ Subscriber Onboarding Loaded")


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

    print("✓ Broker Accounts API Loaded")

except Exception as e:

    print("Broker Accounts API Load Error:", e)


# ======================================
# CLIENT ONBOARDING WORKFLOW
# ======================================

try:

    from api.onboarding.routes import router as client_onboarding_router
    from api.database import Base as ApiBase, engine as api_engine

    app.include_router(client_onboarding_router)
    ApiBase.metadata.create_all(bind=api_engine)

    print("✓ Client Onboarding Workflow Loaded")

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


    print("✓ Performance API Loaded")


except Exception as e:

    print("Performance API Load Error:", e)



# ======================================
# INVESTOR DASHBOARD
# ======================================

try:

    from api.routes.public_investor import router as investor_router
    from api.routes.investor import router as investor_status_router
    from api.auth.routes.investor_login import router as investor_auth_router
    from api.investors.routes.dashboard import router as investor_dashboard_router
    from api.investors.routes.admin import router as admin_investors_router


    app.include_router(

        investor_router,

        tags=["Investor"]

    )

    app.include_router(

        investor_status_router,

        tags=["Investor"]

    )

    app.include_router(investor_auth_router)
    app.include_router(investor_dashboard_router)
    app.include_router(admin_investors_router)


    print("✓ Investor API Loaded")


except Exception as e:

    print("Investor API Load Error:", e)



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


    print("✓ MT5 API Loaded")


except Exception as e:

    print("MT5 API Load Error:", e)



# ======================================
# STARTUP
# ======================================

@app.on_event("startup")
def startup_event():

    print("=" * 40)

    print("BETHEL TRADING TECHNOLOGIES")

    print("QUANT PLATFORM")

    print("=" * 40)

    print()

    print(f"Version: {settings.VERSION}")

    print(f"Environment: {settings.ENVIRONMENT}")

    print()

    print("Modules:")

    print("✓ Configuration Loaded")

    print("✓ Logging Online")

    print(f"✓ {database_status()}")

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

        reload=True

    )
