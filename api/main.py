"""
Bethel Trading Technologies
FastAPI Main Application
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware


# ==========================
# ROUTES
# ==========================

from api.routes import accounts
from api.routes import dashboard
from api.routes.mt5.router import router as mt5_router

from auth.router import router as auth_router



# ==========================
# APP INITIALIZATION
# ==========================

app = FastAPI(
    title="Bethel Trading Technologies API",
    version="1.0"
)



# ==========================
# CORS
# Cloudflare Frontend Support
# ==========================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "https://betheltradingtechnologies.com",
        "https://86207a4a.bethel-1vz.pages.dev",
        "http://localhost",
        "http://127.0.0.1:8000",
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



# ==========================
# TEMPLATE ENGINE
# ==========================

templates = Jinja2Templates(
    directory="dashboard/templates"
)



# ==========================
# API ROUTERS
# ==========================


# Trading Accounts
app.include_router(
    accounts.router
)



# MT5 Bridge
app.include_router(
    mt5_router
)



# Dashboard Analytics
app.include_router(
    dashboard.router
)



# Authentication
app.include_router(
    auth_router
)



# ==========================
# ROOT DASHBOARD PAGE
# ==========================

@app.get("/")
def dashboard_home(
    request: Request
):

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

        "service": "Bethel Trading Technologies API"

    }