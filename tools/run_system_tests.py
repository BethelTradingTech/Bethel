from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import subprocess
import sys
import traceback
import urllib.error
import urllib.request
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


@dataclass
class TestResult:
    area: str
    test: str
    status: str
    detail: str


results: list[TestResult] = []


def record(area: str, test: str, status: str, detail: str) -> None:
    results.append(TestResult(area, test, status, detail))
    mark = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
    print(f"{mark} {area}: {test} - {detail}")


def check(area: str, test: str, action: Callable[[], Any]) -> None:
    try:
        detail = action()
        record(area, test, "PASS", str(detail or "validated"))
    except Exception as error:
        record(area, test, "FAIL", f"{type(error).__name__}: {error}")


def require(condition: bool, detail: str) -> str:
    if not condition:
        raise AssertionError(detail)
    return detail


def http_request(
    method: str,
    url: str,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        method=method,
        headers=headers,
        data=data,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                payload = raw
            return response.status, payload
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = raw
        return error.code, payload


def expect_http(
    name: str,
    method: str,
    url: str,
    expected: set[int],
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    code, payload = http_request(method, url, token, body)
    if code not in expected:
        raise AssertionError(f"HTTP {code}; expected {sorted(expected)}; response={payload}")
    return code, payload


def validate_javascript() -> str:
    files = [
        ROOT / "investor-frontend/js/onboarding.js",
        ROOT / "investor-frontend/js/setup-password.js",
        ROOT / "admin-frontend/js/admin-control.js",
        ROOT / "admin-frontend/js/api.js",
        ROOT / "admin-frontend/js/auth.js",
    ]
    existing = [path for path in files if path.exists()]
    if not existing:
        raise AssertionError("No frontend JavaScript files found")
    for path in existing:
        completed = subprocess.run(
            ["node", "--check", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            raise AssertionError(f"{path.relative_to(ROOT)}: {completed.stderr.strip()}")
    return f"{len(existing)} JavaScript files"


def validate_python() -> str:
    files = []
    for base in (ROOT / "api", ROOT / "main.py"):
        if base.is_file():
            files.append(base)
        elif base.exists():
            files.extend(base.rglob("*.py"))
    files = [
        path for path in files
        if "__pycache__" not in path.parts
        and "backups" not in path.parts
        and "backup" not in path.name.lower()
    ]
    for path in files:
        source = path.read_text(encoding="utf-8-sig")
        compile(source, str(path), "exec")
    return f"{len(files)} Python files"


parser = argparse.ArgumentParser(
    description="Safe automated validation for Bethel Trading Technologies."
)
parser.add_argument("--base-url", default="http://127.0.0.1:8000")
parser.add_argument("--email", default="test@example.com")
parser.add_argument("--password", default=os.getenv("BETHEL_TEST_PASSWORD"))
parser.add_argument("--no-login", action="store_true")
args = parser.parse_args()
base = args.base_url.rstrip("/")

print("=" * 72)
print("BETHEL TRADING TECHNOLOGIES - AUTOMATED SYSTEM VALIDATION")
print("=" * 72)
print("Mode: SAFE READ-ONLY / NEGATIVE SECURITY TESTING")
print("No approval, payment, KYC, MT5 connection, trade or withdrawal is executed.")
print()

check("Source", "Python syntax", validate_python)
check("Source", "JavaScript syntax", validate_javascript)

app = None
schema: dict[str, Any] = {}
engine = None
SessionLocal = None


def load_application() -> str:
    global app, schema, engine, SessionLocal
    warnings.filterwarnings(
        "error",
        message="Duplicate Operation ID.*",
        category=UserWarning,
    )
    from main import app as loaded_app
    from api.database import SessionLocal as session_factory, engine as loaded_engine

    app = loaded_app
    engine = loaded_engine
    SessionLocal = session_factory
    schema = app.openapi()
    return f"{len(schema.get('paths', {}))} OpenAPI paths"


check("Application", "Import and OpenAPI generation", load_application)


required_paths = {
    "Authentication": [
        "/copytrading/auth/login",
        "/copytrading/auth/setup-password",
        "/admin/subscribers/{subscriber_id}/invite",
    ],
    "Onboarding": [
        "/onboarding/plans",
        "/onboarding/{subscriber_id}",
        "/onboarding/{subscriber_id}/subscription",
        "/onboarding/{subscriber_id}/approval",
    ],
    "MT5": [
        "/broker-accounts/link/{subscriber_id}",
        "/mt5/account",
        "/mt5/positions",
    ],
    "KYC": [
        "/kyc/{subscriber_id}/access-token",
        "/kyc/webhook/sumsub",
    ],
    "Payments": [
        "/payments/stripe/{subscriber_id}/checkout",
        "/payments/binance/{subscriber_id}/order",
        "/payments/paypal/{subscriber_id}/order",
        "/payments/wise/{subscriber_id}/instructions",
        "/admin/payments",
    ],
    "Subscriptions": [
        "/subscriptions/{subscriber_id}",
        "/admin/subscriptions",
        "/admin/subscriptions/sweep",
    ],
    "Profit share": [
        "/profit-share/terms",
        "/profit-share/{subscriber_id}/accept",
        "/admin/profit-share",
    ],
    "Legal consent": [
        "/legal/documents",
        "/legal/{subscriber_id}/status",
        "/legal/{subscriber_id}/accept",
        "/admin/legal/acceptances",
    ],
}

for area, paths in required_paths.items():
    check(
        "Routes",
        area,
        lambda paths=paths: require(
            all(path in schema.get("paths", {}) for path in paths),
            f"{len(paths)} required routes",
        ),
    )


expected_tables = {
    "Core": {"copy_subscribers", "client_onboarding", "broker_accounts"},
    "Invitations": {"subscriber_invites"},
    "KYC": set(),
    "Payments": {
        "stripe_payments",
        "binance_payments",
        "paypal_payments",
        "wise_payments",
        "payment_audit",
    },
    "Subscriptions": {"subscription_lifecycle", "subscription_audit"},
    "Profit share": {
        "profit_share_agreements",
        "profit_share_accounts",
        "profit_share_statements",
        "profit_share_audit",
    },
    "Legal consent": {"legal_documents", "legal_acceptances"},
}


def table_names() -> set[str]:
    from sqlalchemy import inspect

    return set(inspect(engine).get_table_names())


if engine is not None:
    actual_tables = table_names()
    for area, tables in expected_tables.items():
        check(
            "Database",
            area,
            lambda tables=tables: require(
                tables.issubset(actual_tables),
                f"{len(tables)} required tables"
                if tables
                else "provider stores use onboarding record",
            ),
        )


def legal_integrity() -> str:
    from api.legal.models import LegalDocument

    db = SessionLocal()
    try:
        documents = (
            db.query(LegalDocument)
            .filter(LegalDocument.active.is_(True))
            .all()
        )
        require(len(documents) == 5, "Exactly five active legal documents required")
        for document in documents:
            digest = hashlib.sha256(document.content.encode("utf-8")).hexdigest()
            require(digest == document.content_hash, f"Hash mismatch: {document.code}")
        return "5 active documents with valid SHA-256 hashes"
    finally:
        db.close()


check("Legal", "Document integrity", legal_integrity)


def profit_share_math() -> str:
    from types import SimpleNamespace
    import api.profit_share.service as service

    original = service.realized_profit_through
    account = SimpleNamespace(
        subscriber_id=999999,
        baseline_cumulative_profit=0.0,
        high_water_mark=1000.0,
        fee_rate=0.20,
        currency="USD",
    )
    try:
        service.realized_profit_through = lambda db, sid, end: 1500.0
        profit = service.projected_accrual(None, account)
        require(profit["eligible_profit"] == 500.0, "Eligible profit must be 500")
        require(profit["projected_fee"] == 100.0, "Bethel fee must be 100")
        require(profit["subscriber_profit_share"] == 400.0, "Subscriber share must be 400")
        service.realized_profit_through = lambda db, sid, end: 800.0
        loss = service.projected_accrual(None, account)
        require(loss["eligible_profit"] == 0.0, "Loss recovery must not be charged")
        require(loss["projected_fee"] == 0.0, "Fee during loss recovery must be zero")
        return "20/80 split and high-water mark"
    finally:
        service.realized_profit_through = original


check("Accounting", "20% profit-share calculations", profit_share_math)


def subscription_dates() -> str:
    from api.subscription_lifecycle.service import period_end

    jan_31 = datetime(2026, 1, 31)
    require(period_end(jan_31, "MONTHLY") == datetime(2026, 2, 28), "Month-end rollover")
    return "monthly period rollover"


check("Subscriptions", "Calendar period logic", subscription_dates)


def activation_gates() -> str:
    source = (ROOT / "api/onboarding/service.py").read_text(encoding="utf-8-sig")
    gates = [
        "profit_share_accepted(db, onboarding.subscriber_id)",
        "all_current_accepted(db, onboarding.subscriber_id)",
        'onboarding.kyc_status == "APPROVED"',
        'onboarding.payment_status == "PAID"',
    ]
    return require(all(gate in source for gate in gates), f"{len(gates)} activation gates")


check("Onboarding", "Activation gates", activation_gates)


def copy_enforcement() -> str:
    allocation = (ROOT / "api/copytrading/allocation.py").read_text(encoding="utf-8-sig")
    sync = (ROOT / "api/copytrading/sync_engine.py").read_text(encoding="utf-8-sig")
    bridge = (ROOT / "api/copytrading/subscriber_bridge.py").read_text(encoding="utf-8-sig")
    require("sweep_subscriptions(db)" in allocation, "Allocation expiry enforcement missing")
    require("sweep_subscriptions(db)" in sync, "Synchronization expiry enforcement missing")
    require("subscriber_can_copy(db, subscriber.id)" in bridge, "Execution gate missing")
    return "allocation, synchronization and execution"


check("Copy trading", "Subscription enforcement", copy_enforcement)


public_tests = [
    ("Health", "GET", "/health", {200}, None),
    ("Plans", "GET", "/onboarding/plans", {200}, None),
    ("Legal documents", "GET", "/legal/documents", {200}, None),
    ("Profit-share terms", "GET", "/profit-share/terms", {200}, None),
]
for name, method, path, expected, body in public_tests:
    check(
        "HTTP public",
        name,
        lambda method=method, path=path, expected=expected, body=body:
        f"HTTP {expect_http(name, method, base + path, expected, body=body)[0]}",
    )

protected_without_login = [
    ("Onboarding", "GET", "/onboarding/5"),
    ("Legal status", "GET", "/legal/5/status"),
    ("Profit share", "GET", "/profit-share/5"),
    ("Subscription", "GET", "/subscriptions/5"),
    ("Admin payments", "GET", "/admin/payments"),
    ("Admin legal", "GET", "/admin/legal/acceptances"),
    ("Admin subscriptions", "GET", "/admin/subscriptions"),
    ("Admin profit share", "GET", "/admin/profit-share"),
]
for name, method, path in protected_without_login:
    check(
        "HTTP authentication",
        name,
        lambda method=method, path=path:
        f"HTTP {expect_http(name, method, base + path, {401})[0]}",
    )

check(
    "HTTP authentication",
    "Public password overwrite disabled",
    lambda: f"HTTP {expect_http('register', 'POST', base + '/copytrading/auth/register', {410}, body={'email':'nobody@example.invalid','password':'Invalid-Test-Only-2026!'})[0]}",
)

token = None
subscriber_id = None
if args.no_login:
    record("Authenticated workflow", "Subscriber login", "SKIP", "--no-login selected")
else:
    password = args.password
    if not password:
        if sys.stdin.isatty():
            password = getpass.getpass(f"Password for test subscriber {args.email}: ")
        else:
            record(
                "Authenticated workflow",
                "Subscriber login",
                "SKIP",
                "Set BETHEL_TEST_PASSWORD or pass --password",
            )
    if password:
        try:
            _, login = expect_http(
                "login",
                "POST",
                base + "/copytrading/auth/login",
                {200},
                body={"email": args.email, "password": password},
            )
            token = login.get("access_token")
            subscriber_id = int(login.get("subscriber_id"))
            require(bool(token), "Login response contains no access token")
            record(
                "Authenticated workflow",
                "Subscriber login",
                "PASS",
                f"subscriber {subscriber_id}",
            )
        except Exception as error:
            record("Authenticated workflow", "Subscriber login", "FAIL", str(error))

if token and subscriber_id:
    own_reads = [
        ("Onboarding status", f"/onboarding/{subscriber_id}"),
        ("Legal consent status", f"/legal/{subscriber_id}/status"),
        ("Profit-share status", f"/profit-share/{subscriber_id}"),
        ("Subscription lifecycle", f"/subscriptions/{subscriber_id}"),
        ("Subscriber record", f"/copytrading/subscribers/{subscriber_id}"),
    ]
    for name, path in own_reads:
        check(
            "Subscriber scope",
            name,
            lambda path=path: f"HTTP {expect_http(name, 'GET', base + path, {200}, token)[0]}",
        )

    other_id = 1 if subscriber_id != 1 else 2
    other_reads = [
        ("Other onboarding", f"/onboarding/{other_id}"),
        ("Other legal status", f"/legal/{other_id}/status"),
        ("Other profit share", f"/profit-share/{other_id}"),
        ("Other subscription", f"/subscriptions/{other_id}"),
        ("Other subscriber record", f"/copytrading/subscribers/{other_id}"),
    ]
    for name, path in other_reads:
        check(
            "Subscriber isolation",
            name,
            lambda path=path: f"HTTP {expect_http(name, 'GET', base + path, {403}, token)[0]}",
        )

    admin_reads = [
        ("Payment administration", "/admin/payments"),
        ("Legal administration", "/admin/legal/acceptances"),
        ("Subscription administration", "/admin/subscriptions"),
        ("Profit-share administration", "/admin/profit-share"),
        ("System settings", "/admin/control/settings"),
    ]
    for name, path in admin_reads:
        check(
            "Role separation",
            name,
            lambda path=path: f"HTTP {expect_http(name, 'GET', base + path, {401, 403}, token)[0]}",
        )
else:
    record(
        "Authenticated workflow",
        "Subscriber scope and role isolation",
        "SKIP",
        "No valid subscriber session",
    )

external_configuration = {
    "Sumsub": ["SUMSUB_APP_TOKEN", "SUMSUB_SECRET_KEY", "SUMSUB_LEVEL_NAME"],
    "Stripe": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
    "Binance Pay": ["BINANCE_PAY_API_KEY", "BINANCE_PAY_PRIVATE_KEY"],
    "PayPal": ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"],
    "Wise": ["WISE_RECIPIENT_NAME", "WISE_ACCOUNT_DETAILS"],
}
for provider, variables in external_configuration.items():
    configured = all(bool(os.getenv(name)) for name in variables)
    if configured:
        record(
            "External configuration",
            provider,
            "PASS",
            "required environment variables present; no real transaction executed",
        )
    else:
        record(
            "External configuration",
            provider,
            "SKIP",
            "test credentials not configured",
        )

REPORTS.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
json_path = REPORTS / f"system-test-{timestamp}.json"
text_path = REPORTS / f"system-test-{timestamp}.txt"
summary = {
    status: sum(1 for row in results if row.status == status)
    for status in ("PASS", "FAIL", "SKIP")
}
payload = {
    "generated_at": datetime.now().isoformat(),
    "base_url": base,
    "mode": "safe-read-only-and-negative-security",
    "summary": summary,
    "results": [asdict(row) for row in results],
}
json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
text_lines = [
    "BETHEL TRADING TECHNOLOGIES - SYSTEM TEST REPORT",
    f"Generated: {payload['generated_at']}",
    f"PASS: {summary['PASS']}  FAIL: {summary['FAIL']}  SKIP: {summary['SKIP']}",
    "",
]
text_lines.extend(
    f"{row.status:4} | {row.area} | {row.test} | {row.detail}"
    for row in results
)
text_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")

print()
print("=" * 72)
print(f"PASS: {summary['PASS']}  FAIL: {summary['FAIL']}  SKIP: {summary['SKIP']}")
print(f"Report: {text_path}")
print(f"JSON:   {json_path}")
print("=" * 72)
if summary["FAIL"]:
    sys.exit(1)
