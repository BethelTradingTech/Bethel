from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, Request

from api.auth.dependency import require_admin

router = APIRouter(prefix="/admin/control", tags=["Admin Control"])
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = DATA_DIR / "admin_control_settings.json"

DEFAULT_SETTINGS = {
    "website": {
        "company_name": "Bethel Trading Technologies",
        "hero_badge": "Smart Trading Systems",
        "hero_title": "Algorithmic Trading Technology for Modern Investors",
        "hero_description": "Discipline-driven execution. Fully transparent algorithms. Rigorous institutional-grade risk management.",
        "primary_cta_text": "View Verified Performance",
        "primary_cta_url": "#performance",
        "contact_email": "info@betheltradingtechnologies.com",
        "contact_phone": "+1 (246) 259-0997",
        "myfxbook_url": "https://www.myfxbook.com",
        "fxblue_url": "https://www.fxblue.com",
        "darwinex_url": "",
        "whatsapp_url": "https://wa.me/12462590997",
        "linkedin_url": "https://www.linkedin.com/company/135675389/",
        "facebook_url": "https://www.facebook.com/profile.php?id=61591695215237",
        "instagram_url": "https://www.instagram.com/betheltradingtech",
        "x_url": "https://x.com/betheltradingt",
        "youtube_url": "https://youtube.com/@betheltradingtech",
        "tiktok_url": "https://www.tiktok.com/@betheltradingtech",
        "risk_disclosure": "Trading foreign exchange, CFDs, and leveraged products carries significant risk. Past performance does not guarantee future results."
    },
    "system": {
        "environment": "DEVELOPMENT",
        "public_url": "https://betheltradingtechnologies.com",
        "investor_portal_url": "/investor-frontend/",
        "subscriber_portal_url": "/investor-frontend/",
        "maintenance_mode": False,
        "subscriber_registration_enabled": True
    }
}

CRITICAL_ADMIN_ROUTES = {
    "/admin/control/settings",
    "/admin/control/routes",
    "/admin/investors",
    "/admin/operations/backups",
    "/admin/operations/security-events",
    "/admin/notifications",
    "/admin/legal/acceptances",
    "/admin/subscriptions",
    "/admin/payments",
    "/copytrading/subscribers",
    "/connector/v1/status",
    "/connector/v1/admin/public-display",
    "/broadcast/v1/admin/control",
    "/performance/analytics",
}


def read_settings() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        saved = {}
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    for section in ("website", "system"):
        merged[section].update(saved.get(section, {}))
    return merged


def write_settings(settings: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = SETTINGS_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    temp.replace(SETTINGS_FILE)


@router.get("/settings")
def get_settings(_: dict = Depends(require_admin)):
    return read_settings()


@router.put("/settings/website")
def update_website(payload: dict[str, Any], _: dict = Depends(require_admin)):
    settings = read_settings()
    settings["website"].update(payload)
    write_settings(settings)
    return {"status": "success", "website": settings["website"]}


@router.put("/settings/system")
def update_system(payload: dict[str, Any], _: dict = Depends(require_admin)):
    settings = read_settings()
    payload["environment"] = settings["system"].get("environment", "DEVELOPMENT")
    settings["system"].update(payload)
    write_settings(settings)
    return {"status": "success", "system": settings["system"]}


@router.get("/routes")
def list_routes(request: Request, _: dict = Depends(require_admin)):
    rows = []
    for route in request.app.routes:
        methods = sorted(m for m in getattr(route, "methods", []) if m not in {"HEAD", "OPTIONS"})
        rows.append({"path": getattr(route, "path", ""), "name": getattr(route, "name", ""), "methods": methods})
    return {"status": "success", "total": len(rows), "routes": sorted(rows, key=lambda x: x["path"])}


@router.get("/health")
def admin_health(request: Request, admin: dict = Depends(require_admin)):
    mounted_paths = {getattr(route, "path", "") for route in request.app.routes}
    missing = sorted(path for path in CRITICAL_ADMIN_ROUTES if path not in mounted_paths)
    return {
        "status": "healthy" if not missing else "degraded",
        "administrator_role": admin.get("role"),
        "critical_routes_expected": len(CRITICAL_ADMIN_ROUTES),
        "critical_routes_mounted": len(CRITICAL_ADMIN_ROUTES) - len(missing),
        "missing_routes": missing,
        "read_only_trading": True,
        "execution_owner": "METATRADER_EA",
    }


@router.get("/public-settings")
def public_settings():
    settings = read_settings()
    return {"website": settings["website"], "system": {"maintenance_mode": settings["system"]["maintenance_mode"]}}
