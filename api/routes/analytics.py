"""Bethel Trading Technologies analytics API routes."""

from fastapi import APIRouter, Request

from analytics.equity_curve import EquityCurve
from analytics.performance import PerformanceAnalytics
from api.auth.dependency import check_auth
from api.services.performance_engine import get_performance_analytics
from mt5_connector.history import MT5History

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _require_authenticated(request: Request):
    auth = check_auth(request)
    if auth:
        return auth
    return None


@router.get("/performance")
def performance(request: Request):
    auth = _require_authenticated(request)
    if auth:
        return auth
    try:
        history = MT5History().get_history()
        result = PerformanceAnalytics(history).calculate()
        return {"status": "success", "performance": result}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/investor-performance")
def investor_performance(request: Request):
    """Return the existing unified, read-only report to authenticated users."""
    auth = _require_authenticated(request)
    if auth:
        return auth
    try:
        data = get_performance_analytics()
        if "consistency_score" in data:
            data["consistency_score"] = float(data["consistency_score"])
        return data
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/equity")
def equity_curve(request: Request):
    auth = _require_authenticated(request)
    if auth:
        return auth
    try:
        history = MT5History().get_history()
        engine = EquityCurve(history, starting_balance=100000)
        return {"status": "success", "equity": engine.calculate()}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/status")
def analytics_status():
    return {
        "module": "Analytics Engine",
        "status": "online",
        "company": "Bethel Trading Technologies",
    }
