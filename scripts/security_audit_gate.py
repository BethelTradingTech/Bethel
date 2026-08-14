"""Static security regression gate for Bethel production safeguards.

This intentionally avoids importing the FastAPI application so CI can verify
critical controls without requiring production secrets or a live database.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    data = text(path)
    missing = [needle for needle in needles if needle not in data]
    if missing:
        raise SystemExit(f"SECURITY GATE FAIL {path}: missing {missing}")


def forbid(path: str, *needles: str) -> None:
    data = text(path)
    present = [needle for needle in needles if needle in data]
    if present:
        raise SystemExit(f"SECURITY GATE FAIL {path}: forbidden {present}")


# Supported administrator login: throttled and hardened cookie.
require(
    "api/auth/routes/auth.py",
    "check_login_allowed(request, data.identifier)",
    "record_login_failure(request, data.identifier)",
    "httponly=True",
    "secure=True",
    'samesite="strict"',
)

# Legacy login must never mint a token or cookie again.
require("api/auth/routes.py", "status_code=410", "Legacy administrator login is disabled")
forbid("api/auth/routes.py", "set_cookie(", "create_token(")

# Platform trade execution remains blocked.
require(
    "main.py",
    "permanent_read_only_trading_guard",
    "Bethel is permanently read-only",
    '"/copytrading/bridge-execute"',
    '"/copyhub/v1/"',
)

# Connector requests must remain signed, time-bound and replay-aware.
require(
    "api/mt5_ingest/routes.py",
    "MT5_CONNECTOR_SECRET",
    "x-bethel-signature",
    "MAX_CLOCK_SKEW_SECONDS = 300",
    "hmac.compare_digest(expected, supplied)",
    "ConnectorNonce",
)

# Broadcast/media worker authentication and expiring/revocable review links.
require(
    "broadcast-worker/app.py",
    "hmac.compare_digest(v,SECRET)",
    "MEDIA_SHARE_TTL_SECONDS",
    '"share_expires_at"',
    '"share_revoked"',
    "@app.post('/media/revoke/{token}')",
    '"Cache-Control":"private, no-store"',
)

# Admin API remains Super-Admin gated for media generation/list/revocation.
require(
    "api/broadcast/routes.py",
    "@router.get('/admin/media')",
    "@router.post('/admin/media/generate')",
    "@router.post('/admin/media/revoke/{token}')",
    "Depends(require_super_admin)",
)

# Public KYC readiness must never disclose service topology, storage or datasets.
require(
    "render_app.py",
    "sanitize_native_kyc_readiness",
    "_native_public_state",
    '@app.get("/admin/kyc/native/readiness")',
    "Depends(require_admin)",
    '"Cache-Control": "no-store"',
)
forbid(
    "render_app.py",
    '"native_kyc": native',
    '"app_token_configured"',
    '"level_configured"',
    '"webhook_verification"',
)

print("PASS: Bethel security audit regression gate")
