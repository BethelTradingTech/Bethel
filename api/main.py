"""
Bethel Trading Technologies
FastAPI Main Application

Institutional Quant Trading Platform
"""


# ==========================
# FASTAPI CORE
# ==========================

from fastapi import FastAPI, Request

from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from fastapi.middleware.cors import CORSMiddleware





# ==========================
# DATABASE
# ==========================

from api.database import engine

from api.models import Base





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

    description=
    "Institutional Algorithmic Trading & Investor Portal",

    version="1.0"

)





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


        "https://betheltradingtechnologies.com",


        "https://86207a4a.bethel-1vz.pages.dev",


        "http://localhost",


        "http://127.0.0.1:8000"


    ],


    allow_credentials=True,


    allow_methods=["*"],


    allow_headers=["*"]

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



# Dashboard

app.include_router(

    dashboard.router

)



# Analytics

app.include_router(

    analytics.router

)



# Risk Management

app.include_router(

    risk.router

)



# MT5 Connection

app.include_router(

    mt5_router

)



# Performance Analytics

app.include_router(

    performance_router

)



# Authentication

app.include_router(

    auth_router

)


app.include_router(

    investor_auth_router

)



# Investor Portfolio Management

app.include_router(

    portfolio_router

)



# Investor MT5 Account Assignment

app.include_router(

    mt5_accounts_router

)



# Investor Dashboard

app.include_router(

    investor_router

)


# Investor Dashboard API

app.include_router(

    investor_dashboard_router

)





# ==========================
# LOGIN PAGE
# ==========================


@app.get("/login")

def login_page(

    request: Request

):


    return templates.TemplateResponse(

        request=request,

        name="login.html"

    )





# ==========================
# HOME DASHBOARD
# ==========================


@app.get("/")

def dashboard_home(

    request: Request

):


    auth = check_auth(request)



    if auth:

        return auth



    return templates.TemplateResponse(

        request=request,

        name="index.html",

        context={


            "company":

            "Bethel Trading Technologies"


        }

    )





# ==========================
# HEALTH CHECK
# ==========================


@app.get("/health")

def health():


    return {


        "status":

        "online",


        "service":

        "Bethel Trading Technologies API",


        "version":

        "1.0"


    }