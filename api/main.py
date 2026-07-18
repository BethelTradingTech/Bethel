from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.routes import accounts
from api.routes import dashboard
from api.routes.mt5.router import router as mt5_router


app = FastAPI(
    title="Bethel Trading Technologies API",
    version="1.0"
)


# ==========================
# Dashboard Static Files
# ==========================

app.mount(
    "/static",
    StaticFiles(directory="dashboard/static"),
    name="static"
)


templates = Jinja2Templates(
    directory="dashboard/templates"
)


# ==========================
# API ROUTES
# ==========================

# Trading Accounts
app.include_router(
    accounts.router
)


# MT5 Connection / Trading
app.include_router(
    mt5_router
)


# Combined Dashboard Data API
app.include_router(
    dashboard.router
)


# ==========================
# DASHBOARD HOME PAGE
# ==========================

@app.get("/")
def dashboard_home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "company": "Bethel Trading Technologies"
        }
    )