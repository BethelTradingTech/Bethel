from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, Request

from api.auth.dependency import require_admin
from api.admin.linkedin_routes import router as linkedin_router
from api.admin.tiktok_routes import router as tiktok_router

router = APIRouter(prefix="/admin/control", tags=["Admin Control"])
router.include_router(linkedin_router)
router.include_router(tiktok_router)
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
        "secondary_cta_text": "Partner With Us",
        "secondary_cta_url": "#contact",
        "registration_cta_text": "Request Access",
        "registration_cta_url": "#contact",
        "prelaunch_label": "PRE-LAUNCH NOTICE",
        "prelaunch_text": "Bethel is currently in its pre-launch and commercial readiness phase. Public registration and onboarding are open. Account activation remains subject to the applicable identity verification, compliance, legal, payment, trading-account linking, copier activation, and final Super Admin approval requirements.",
        "public_notice_text": "Bethel Quant Trading Technologies Limited is currently in its pre-launch and commercial readiness phase. The information, technology demonstrations, live trading broadcasts, performance records, and platform features presented on this website are provided to demonstrate the capabilities and ongoing development of the Bethel technology ecosystem. Public customer services and any activities requiring regulatory authorization will only be made available in applicable jurisdictions once the necessary legal, compliance, and regulatory requirements have been satisfied. Nothing presented on this website constitutes an offer, solicitation, investment recommendation, or guarantee of future trading performance.",
        "privacy_policy_url": "https://betheltradingtechnologies.com/privacy-policy.html",
        "about_title": "About Us",
        "about_subtitle": "Our philosophy is built on transparent execution and mathematical discipline.",
        "about_paragraph_1": "Bethel Trading Technologies develops elite algorithmic trading systems designed to navigate today's volatile markets with precision.",
        "about_paragraph_2": "Rather than relying on human emotion or market speculation, our software targets systematic inefficiencies in order to maintain a structured approach to wealth preservation and capital appreciation.",
        "services_title": "Our Services",
        "services_subtitle": "Innovative technology designed to elevate modern investment portfolios.",
        "service_1_title": "Automated Trading Systems",
        "service_1_text": "Deploy custom-built algorithms designed to monitor, track, and execute trades instantly without emotional bias.",
        "service_2_title": "Copy Trading Solutions",
        "service_2_text": "Seamlessly mirror active algorithmic portfolios directly into your personal broker account with real-time replication.",
        "service_3_title": "Trading Signal Services",
        "service_3_text": "Receive high-probability alerts and algorithmic insights curated by our core research team.",
        "service_4_title": "Strategy Research & Dev",
        "service_4_text": "Rigorous historical backtesting, modeling, and system optimization based on institutional-grade criteria.",
        "service_5_title": "Investor Partnerships",
        "service_5_text": "Tailored capital management solutions built to fit specific risk appetites and return profiles.",
        "live_title": "LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1",
        "live_description": "Live read-only Bethel Terminal 1 broadcast and account telemetry, followed by the active master's monthly and yearly return record.",
        "returns_title": "Monthly & Yearly Returns",
        "contact_title": "Let's Build the Future of Your Capital",
        "contact_description": "Get in touch to request our historical pitch books, discuss technical API integration, or learn how to partner with our automated trading systems.",
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
        "risk_disclosure": "Trading foreign exchange, CFDs, and leveraged products carries significant risk. Past performance does not guarantee future results.",
        "public_controls": {
            "site_enabled": True,
            "show_navigation": True,
            "show_hero": True,
            "show_prelaunch_notice": False,
            "show_public_notice_disclosure": False,
            "show_about": True,
            "show_services": True,
            "show_live_broadcast": True,
            "show_live_telemetry": True,
            "show_starting_balance": True,
            "show_monthly_yearly_returns": True,
            "show_reviews": True,
            "show_contact": True,
            "show_contact_form": True,
            "show_social_links": True,
            "show_footer": True,
            "show_request_access": True,
            "show_performance_cta": True,
            "show_partner_cta": True,
            "show_ai_assistant": True
        }
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
    "/admin/control/integrations/linkedin/status",
    "/admin/control/integrations/tiktok/status",
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


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def read_settings() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        saved = {}
    return _deep_merge(json.loads(json.dumps(DEFAULT_SETTINGS)), saved)


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
    _deep_merge(settings["website"], payload)
    write_settings(settings)
    return {"status": "success", "website": settings["website"]}


@router.put("/settings/system")
def update_system(payload: dict[str, Any], _: dict = Depends(require_admin)):
    settings = read_settings()
    payload["environment"] = settings["system"].get("environment", "DEVELOPMENT")
    _deep_merge(settings["system"], payload)
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
    return {
        "website": settings["website"],
        "system": {
            "maintenance_mode": bool(settings["system"].get("maintenance_mode", False)),
            "subscriber_registration_enabled": bool(settings["system"].get("subscriber_registration_enabled", True)),
        },
    }
