"""Static safety checks for Bethel Super Admin contracts.

This intentionally uses only the Python standard library so it can run in CI
without importing application modules or requiring production secrets.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"ADMIN CONTRACT FAILED: {message}")


admin_router = read("api/admin/router.py")
auth_dependency = read("api/auth/dependency.py")
main = read("main.py")
admin_api = read("admin-frontend/js/api.js")
admin_control = read("admin-frontend/js/admin-control.js")

require(
    "from api.auth.dependency import require_admin" in admin_router,
    "admin control must use the centralized require_admin dependency",
)
require(
    "def require_admin(" not in admin_router,
    "admin control must not define a second admin-role checker",
)
require(
    'ADMIN_ROLES = {"admin", "super_admin"}' in auth_dependency,
    "central admin dependency must accept admin and super_admin",
)
require(
    '"/copyhub/v1/"' in main and "permanent_read_only_trading_guard" in main,
    "the permanent read-only trading guard must continue protecting CopyHub mutations",
)
require(
    '"/admin/control/health"' not in admin_control,
    "admin-control.js should not hard-code a second health implementation",
)
require(
    'localStorage.getItem("bethel_access_token")' in admin_api,
    "admin API client must continue sending the authenticated admin bearer token",
)

critical_frontend_endpoints = (
    "/admin/control/settings",
    "/admin/operations/backups",
    "/admin/notifications",
    "/admin/legal/acceptances",
    "/admin/subscriptions",
    "/admin/payments",
    "/connector/v1/admin/public-display",
    "/broadcast/v1/admin/control",
)
combined_frontend = admin_api + "\n" + admin_control
for endpoint in critical_frontend_endpoints:
    require(endpoint in combined_frontend, f"frontend lost critical admin endpoint {endpoint}")

print("Bethel admin contract checks passed")
