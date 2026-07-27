from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

checks = []


def result(name: str, status: str, detail: str):
    checks.append({"name": name, "status": status, "detail": detail})
    print(f"[{status}] {name}: {detail}")


def secret(name: str):
    value = os.getenv(name, "")
    if len(value) >= 64:
        result(name, "PASS", f"configured ({len(value)} characters)")
    else:
        result(name, "FAIL", "missing or shorter than 64 characters")


secret("JWT_SECRET_KEY")
secret("SUBSCRIBER_JWT_SECRET_KEY")

source = (ROOT / "main.py").read_text(encoding="utf-8-sig")
subscriber_security = (ROOT / "api/security.py").read_text(encoding="utf-8-sig")
legacy_security = (ROOT / "api/auth/security.py").read_text(encoding="utf-8-sig")
result(
    "Hardcoded subscriber secret removed",
    "PASS" if "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_KEY" not in subscriber_security else "FAIL",
    "source inspection",
)
result(
    "Hardcoded legacy admin password removed",
    "PASS" if "Bethel@123" not in legacy_security else "FAIL",
    "source inspection",
)
result(
    "Production CORS",
    "PASS" if "PRODUCTION_ORIGINS" in source and 'allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]' in source else "FAIL",
    "explicit origins, methods and headers",
)
result(
    "Reload disabled",
    "PASS" if "reload=True" not in source else "FAIL",
    "production process configuration",
)

required_tables = {
    "backup_records",
    "security_events",
    "email_deliveries",
    "subscriber_password_resets",
    "legal_documents",
    "legal_acceptances",
}
try:
    from api.database import engine
    from sqlalchemy import inspect

    tables = set(inspect(engine).get_table_names())
    missing = sorted(required_tables - tables)
    result(
        "Operational database tables",
        "PASS" if not missing else "FAIL",
        "all present" if not missing else f"missing: {missing}",
    )
except Exception as error:
    result("Operational database tables", "FAIL", str(error))

try:
    from api.operations.backup import BACKUP_DIRECTORY, verify_backup

    backups = sorted(BACKUP_DIRECTORY.glob("bethel-*.db"), key=lambda p: p.stat().st_mtime)
    if not backups:
        raise RuntimeError("No verified backups found")
    verification = verify_backup(backups[-1].name)
    result(
        "Latest database backup",
        "PASS" if verification["valid"] else "FAIL",
        f"{backups[-1].name}; {verification['size_bytes']} bytes",
    )
except Exception as error:
    result("Latest database backup", "FAIL", str(error))

for provider, variables in {
    "SMTP": ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"],
    "Sumsub": ["SUMSUB_APP_TOKEN", "SUMSUB_SECRET_KEY", "SUMSUB_LEVEL_NAME"],
    "Stripe": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
    "Binance Pay": ["BINANCE_PAY_API_KEY", "BINANCE_PAY_SECRET_KEY"],
    "PayPal": ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"],
    "Wise": ["WISE_RECIPIENT_NAME", "WISE_ACCOUNT_DETAILS"],
}.items():
    configured = all(os.getenv(name) for name in variables)
    result(
        f"{provider} production configuration",
        "PASS" if configured else "WARN",
        "configured" if configured else "not configured",
    )

try:
    request = urllib.request.Request(
        "https://api.betheltradingtechnologies.com/health",
        headers={"User-Agent": "Bethel-Readiness/1.0"},
    )
    with urllib.request.urlopen(
        request,
        timeout=20,
        context=ssl.create_default_context(),
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
        healthy = response.status == 200 and payload.get("status") == "healthy"
        result(
            "Public HTTPS API",
            "PASS" if healthy else "FAIL",
            f"HTTP {response.status}; status={payload.get('status')}",
        )
except Exception as error:
    result("Public HTTPS API", "FAIL", str(error))

summary = {
    status: sum(1 for check in checks if check["status"] == status)
    for status in ("PASS", "FAIL", "WARN")
}
report = {
    "summary": summary,
    "checks": checks,
}
report_path = ROOT / "reports" / "production-readiness.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print()
print(f"PASS: {summary['PASS']}  FAIL: {summary['FAIL']}  WARN: {summary['WARN']}")
print("Report:", report_path)
if summary["FAIL"]:
    raise SystemExit(1)
