"""
Bethel Trading Technologies
FastAPI Main Application
"""


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
# ROUTES
# ==========================

from api.routes import accounts

from api.routes import dashboard

from api.routes import analytics

from api.routes import risk


from api.routes.mt5.router import router as mt5_router

from api.routes.performance.router import router as performance_router


from api.auth.routes import router as auth_router


from dashboard.investor_router import router as investor_router



from api.auth.dependency import check_auth





# ==========================
# CREATE APP
# ==========================


app = FastAPI(

    title="Bethel Trading Technologies API",

    version="1.0"

)





# ==========================
# DATABASE INIT
# ==========================


Base.metadata.create_all(

    bind=engine

)





# ==========================
# START SERVICES
# ==========================


start_scheduler()





# ==========================
# CORS
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
# STATIC
# ==========================


app.mount(

    "/static",

    StaticFiles(

        directory="dashboard/static"

    ),

    name="static"

)





# ==========================
# TEMPLATES
# ==========================


templates = Jinja2Templates(

    directory="dashboard/templates"

)





# ==========================
# ROUTERS
# ==========================


app.include_router(

    accounts.router

)


app.include_router(

    dashboard.router

)


app.include_router(

    analytics.router

)


app.include_router(

    risk.router

)


app.include_router(

    mt5_router

)


app.include_router(

    performance_router

)


app.include_router(

    auth_router

)


app.include_router(

    investor_router

)





# ==========================
# LOGIN
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

            "company":

            "Bethel Trading Technologies"

        }

    )





# ==========================
# HEALTH
# ==========================


@app.get("/health")

def health():

    return {


        "status":

        "online",


        "service":

        "Bethel Trading Technologies API"


    }
