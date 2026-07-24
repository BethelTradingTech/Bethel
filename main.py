"""
Bethel Trading Technologies

Main Platform Controller
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.logger import get_logger
from database.database import database_status

logger = get_logger("BETHEL_SYSTEM")

app = FastAPI(
    title="Bethel Trading Technologies",
    description="Institutional Algorithmic Trading & Copy Trading Platform",
    version=settings.VERSION
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
        prefix="/copytrading",
        tags=["Copy Subscribers"]
    )
    print("✓ Subscriber API Loaded")
except Exception as e:
    print("Subscriber API Load Error:", e)

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

    app.include_router(
        investor_router,
        tags=["Investor"]
    )
    print("✓ Investor API Loaded")
except Exception as e:
    print("Investor API Load Error:", e)

# ======================================
# MT5
# ======================================

try:
    from api.routes.mt5.router import router as mt5_router

    app.include_router(
        mt5_router,
        prefix="",
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