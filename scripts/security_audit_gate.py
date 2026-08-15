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


require(
    "api/auth/routes/auth.py",
    "check_login_allowed(request, data.identifier)",
    "record_login_failure(request, data.identifier)",
    "httponly=True",
    "secure=True",
    'samesite="strict"',
    '@router.post("/logout")',
    "response.delete_cookie(",
)

require(
    "api/copytrading/subscriber_auth_routes.py",
    "check_login_allowed(request, email)",
    'key="subscriber_access_token"',
    "httponly=True",
    "secure=True",
    'samesite="strict"',
    '@router.post("/logout")',
    "ACCESS_TOKEN_EXPIRE_MINUTES * 60",
    "token_hash == _token_hash(data.token)",
    "record.used_at = datetime.utcnow()",
)

require(
    "api/auth/dependency.py",
    'request.cookies.get("subscriber_access_token")',
    'subscriber_payload.get("token_type") != "subscriber"',
    'subscriber_payload.get("subscriber_id") != subscriber_id',
    'status_code=403, detail="Subscriber access denied"',
    'payload.get("role") != "super_admin"',
)

# Security alerts use the existing SMTP path, suppress duplicates, and never
# become a prerequisite for enforcement.
require(
    "api/security_alerts.py",
    "SECURITY_ALERT_EMAIL",
    "SMTP_FROM_EMAIL",
    "SECURITY_ALERT_DEDUP_MINUTES",
    'message_type="SECURITY_ALERT"',
    "deduplication_key=deduplication_key",
)
require(
    "api/auth/rate_limit.py",
    "send_security_alert(",
    'event="Authentication abuse blocked"',
    'event="Registration abuse blocked"',
)
require(
    "scripts/security_compliance_snapshot.py",
    "send_security_alert(",
    'event="Production compliance check failed"',
)

require("api/auth/routes.py", "status_code=410", "Legacy administrator login is disabled")
forbid("api/auth/routes.py", "set_cookie(", "create_token(")

require(
    "api/production_security.py",
    '"X-Content-Type-Options"',
    '"X-Frame-Options"',
    '"Strict-Transport-Security"',
    '"Permissions-Policy"',
    '"X-Permitted-Cross-Domain-Policies"',
    '"Cache-Control"',
    '"/copytrading/auth/register"',
    '"/copytrading/auth/resend-verification"',
)

require(
    "main.py",
    "PRODUCTION_ORIGINS",
    '"https://betheltradingtechnologies.com"',
    '"https://www.betheltradingtechnologies.com"',
    "allow_credentials=True",
)
forbid("main.py", 'allow_origins=["*"]')

require(
    "main.py",
    "permanent_read_only_trading_guard",
    "Bethel is permanently read-only",
    '"/copytrading/bridge-execute"',
    '"/copyhub/v1/"',
)

require(
    "api/mt5_ingest/routes.py",
    "MT5_CONNECTOR_SECRET",
    "x-bethel-signature",
    "MAX_CLOCK_SKEW_SECONDS = 300",
    "hmac.compare_digest(expected, supplied)",
    "ConnectorNonce",
)

require(
    "broadcast-worker/app.py",
    "hmac.compare_digest(v,SECRET)",
    "MEDIA_SHARE_TTL_SECONDS",
    '"share_expires_at"',
    '"share_revoked"',
    "@app.post('/media/revoke/{token}')",
    '"Cache-Control":"private, no-store"',
)

require(
    "api/broadcast/routes.py",
    "@router.get('/admin/media')",
    "@router.post('/admin/media/generate')",
    "@router.post('/admin/media/revoke/{token}')",
    "Depends(require_super_admin)",
)

require(
    "api/kyc/native_routes.py",
    "Depends(require_subscriber_or_admin)",
    "MAX_UPLOAD",
    "duplicate = db.query(BethelKYCSession)",
    "challenge_consumed_at",
)
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

require(
    "render.yaml",
    "bethel-sanctions-refresh",
    "python scripts/refresh_bethel_sanctions.py",
    "bethel-security-compliance-check",
    "python scripts/security_compliance_snapshot.py",
    "fromDatabase:",
    "property: connectionString",
)

print("PASS: Bethel combined security audit regression gate")
