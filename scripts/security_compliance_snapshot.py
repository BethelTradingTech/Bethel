"""Emit a non-secret production security/compliance evidence snapshot."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from api.database import SessionLocal
from api.kyc.native_models import BethelScreeningDataset
from api.security_alerts import send_security_alert

API_BASE = os.getenv("BETHEL_PUBLIC_API_BASE", "https://api.betheltradingtechnologies.com").rstrip("/")


def get_json(path: str) -> tuple[int, dict]:
    request = Request(API_BASE + path, headers={"User-Agent": "bethel-security-monitor/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return 0, {"error": type(exc).__name__}


def main() -> int:
    health_code, health = get_json("/health")
    ready_code, ready = get_json("/ready")
    kyc_code, kyc = get_json("/kyc/native/readiness")

    db = SessionLocal()
    try:
        dataset = (
            db.query(BethelScreeningDataset)
            .filter(
                BethelScreeningDataset.dataset_type == "sanctions",
                BethelScreeningDataset.active.is_(True),
            )
            .order_by(BethelScreeningDataset.id.desc())
            .first()
        )
        sanctions = None if dataset is None else {
            "dataset_id": dataset.id,
            "source": dataset.source_name,
            "active": bool(dataset.active),
        }
    finally:
        db.close()

    checks = {
        "api_health": health_code == 200 and health.get("status") == "healthy",
        "api_ready": ready_code == 200 and ready.get("status") == "ready",
        "native_kyc": kyc_code == 200 and kyc.get("available") is True,
        "sanctions_dataset_active": bool(sanctions and sanctions["active"]),
    }
    passed = all(checks.values())
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "checks": checks,
        "sanctions_dataset": sanctions,
        "overall_status": "PASS" if passed else "FAIL",
    }
    print(json.dumps(evidence, sort_keys=True))

    if not passed:
        failed = ", ".join(name for name, ok in checks.items() if not ok)
        send_security_alert(
            event="Production compliance check failed",
            severity="critical",
            summary="One or more Bethel production security/readiness controls failed.",
            details=f"Failed checks: {failed}",
        )

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
