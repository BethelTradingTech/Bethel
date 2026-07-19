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


# Authentication
from api.auth.routes.auth import router as auth_router



logger = get_logger(
    "BETHEL_SYSTEM"
)


# ======================================
# CREATE FASTAPI APPLICATION
# ======================================


app = FastAPI(

    title="Bethel Trading Technologies",

    description=
    "Algorithmic Trading Technology Platform",

    version=settings.VERSION

)


# ======================================
# CORS CONFIGURATION
# ======================================


app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)


# ======================================
# PLATFORM STARTUP
# ======================================


def start_platform():


    print("=" * 40)

    print(
        "BETHEL TRADING TECHNOLOGIES"
    )

    print(
        "QUANT PLATFORM"
    )

    print("=" * 40)



    print()


    print(
        f"Version: {settings.VERSION}"
    )


    print(
        f"Environment: {settings.ENVIRONMENT}"
    )


    print()


    print("Modules:")


    print(
        "✓ Configuration Loaded"
    )


    logger.info(
        "Bethel Trading Technologies Started"
    )


    print(
        "✓ Logging Online"
    )


    print(
        f"✓ {database_status()}"
    )


    print()


    print(
        "System Status: READY"
    )


    print("=" * 40)


# ======================================
# ROOT TEST ROUTES
# ======================================


@app.get("/")
def home():

    return {

        "system":
        "Bethel Trading Technologies",

        "status":
        "online",

        "version":
        settings.VERSION

    }




@app.get("/health")
def health():

    return {

        "status":
        "healthy",

        "database":
        database_status()

    }


# ======================================
# STARTUP EVENT
# ======================================


@app.on_event("startup")
def startup_event():

    start_platform()


# ======================================
# AUTHENTICATION API
# ======================================


try:

    app.include_router(

        auth_router,

        tags=[
            "Authentication"
        ]

    )


    print(
        "✓ Authentication API Loaded"
    )


except Exception as e:


    print(
        "Authentication API Load Error:",
        e
    )


# ======================================
# PERFORMANCE API
# ======================================


try:

    from api.routes.performance.router import router as performance_router


    app.include_router(

        performance_router,

        prefix="/performance",

        tags=[
            "Performance"
        ]

    )


    print(
        "✓ Performance API Loaded"
    )


except Exception as e:


    print(
        "Performance API Load Error:",
        e
    )


# ======================================
# INVESTOR DASHBOARD API
# ======================================


try:

    from api.routes.public_investor import router as investor_router


    app.include_router(

        investor_router,

        tags=[
            "Investor"
        ]

    )


    print(
        "✓ Investor API Loaded"
    )


except Exception as e:


    print(
        "Investor API Load Error:",
        e
    )


# ======================================
# MT5 CONNECTION API
# ======================================


try:

    from api.routes.mt5 import router as mt5_router


    app.include_router(

        mt5_router,

        prefix="/mt5",

        tags=[
            "MT5"
        ]

    )


    print(
        "✓ MT5 API Loaded"
    )


except Exception as e:


    print(
        "MT5 API Load Error:",
        e
    )


# ======================================
# APPLICATION RUNNER
# ======================================


if __name__ == "__main__":


    import uvicorn


    uvicorn.run(

        "main:app",

        host="127.0.0.1",

        port=8000,

        reload=True

    )


