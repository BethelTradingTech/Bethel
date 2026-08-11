import base64
import hashlib
import os
import re
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.orm import Session

from api.kyc.native_models import BethelKYCCheck, BethelKYCEvidence, BethelKYCSession, BethelScreeningDataset, BethelScreeningEntry


@dataclass
class CheckResult:
    check_type: str
    status: str
    score: float | None = None
    reasons: list[str] | None = None
    evidence: dict | None = None

    def __post_init__(self):
        self.reasons = self.reasons or []
        self.evidence = self.evidence or {}


def _key() -> bytes:
    raw = (os.getenv("KYC_ENCRYPTION_KEY") or "").strip()
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception as exc:
        raise RuntimeError("KYC_ENCRYPTION_KEY must be URL-safe base64") from exc
    if len(decoded) != 32:
        raise RuntimeError("KYC_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return decoded


def _root() -> Path:
    root = Path((os.getenv("KYC_STORAGE_ROOT") or "/var/data/bethel-kyc").strip())
    root.mkdir(parents=True, exist_ok=True)
    return root


def store_evidence(subscriber_id: int, reference: str, category: str, data: bytes) -> tuple[str, str]:
    digest = hashlib.sha256(data).hexdigest()
    nonce = secrets.token_bytes(12)
    aad = f"bethel:{subscriber_id}:{reference}:{category}".encode()
    encrypted = nonce + AESGCM(_key()).encrypt(nonce, data, aad)
    directory = _root() / str(subscriber_id) / reference
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{category}-{secrets.token_hex(8)}.bin"
    path = directory / filename
    path.write_bytes(encrypted)
    return str(path.relative_to(_root())).replace("\\", "/"), digest


def load_evidence(subscriber_id: int, reference: str, category: str, storage_key: str) -> bytes:
    root = _root().resolve()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise RuntimeError("Invalid KYC storage key")
    raw = path.read_bytes()
    nonce, ciphertext = raw[:12], raw[12:]
    aad = f"bethel:{subscriber_id}:{reference}:{category}".encode()
    return AESGCM(_key()).decrypt(nonce, ciphertext, aad)


def _service(base_env: str, key_env: str, path: str, payload: dict, check_type: str, timeout: int = 90) -> CheckResult:
    base = (os.getenv(base_env) or "").rstrip("/")
    key = (os.getenv(key_env) or "").strip()
    if not base or not key:
        return CheckResult(check_type, "not_available", reasons=[f"{check_type} service is not configured"])
    try:
        response = requests.post(
            f"{base}/{path.lstrip('/')}",
            json=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
    except Exception as exc:
        return CheckResult(check_type, "not_available", reasons=[f"{check_type} service unavailable: {type(exc).__name__}"])
    raw = str(body.get("status") or body.get("result") or "review").lower()
    status = "passed" if raw in {"passed", "clear", "clean", "valid", "success"} else "failed" if raw in {"failed", "infected", "malicious", "invalid", "blocked", "fraud"} else "review"
    try:
        score = float(body.get("score")) if body.get("score") is not None else None
    except (TypeError, ValueError):
        score = None
    reasons = body.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    return CheckResult(check_type, status, score, [str(x) for x in reasons], body)


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", (value or "").lower()).strip()


def sanctions_check(db: Session, full_name: str, dob: date | None) -> CheckResult:
    dataset = db.query(BethelScreeningDataset).filter(BethelScreeningDataset.dataset_type == "sanctions", BethelScreeningDataset.active.is_(True)).order_by(BethelScreeningDataset.id.desc()).first()
    if dataset is None:
        return CheckResult("sanctions", "not_available", reasons=["No active Bethel sanctions dataset"])
    max_age = max(1, int(os.getenv("AML_DATASET_MAX_AGE_DAYS", "2")))
    effective = dataset.effective_date or date.today()
    if (date.today() - effective).days > max_age:
        return CheckResult("sanctions", "not_available", reasons=["Bethel sanctions dataset is stale"])
    target = _norm(full_name)
    best = None
    best_score = 0.0
    for row in db.query(BethelScreeningEntry).filter(BethelScreeningEntry.dataset_id == dataset.id).all():
        candidates = [row.primary_name] + list(row.aliases or [])
        for candidate in candidates:
            score = SequenceMatcher(None, target, _norm(candidate)).ratio()
            if score > best_score:
                best, best_score = row, score
    if best is not None and best_score >= 0.94:
        dob_conflict = bool(dob and best.date_of_birth and dob != best.date_of_birth)
        if not dob_conflict:
            return CheckResult("sanctions", "review", round(best_score * 100, 2), ["Potential sanctions name match requires Compliance review"], {"source": dataset.source_name, "source_reference": best.source_reference})
    return CheckResult("sanctions", "passed", 100.0, evidence={"dataset_id": dataset.id, "source": dataset.source_name})


def record_check(db: Session, session: BethelKYCSession, result: CheckResult, version: str):
    db.add(BethelKYCCheck(session_id=session.id, subscriber_id=session.subscriber_id, check_type=result.check_type, status=result.status, score=result.score, reasons=result.reasons, evidence=result.evidence, engine_version=version))


def latest_checks(db: Session, session_id: int) -> dict[str, BethelKYCCheck]:
    rows = db.query(BethelKYCCheck).filter(BethelKYCCheck.session_id == session_id).order_by(BethelKYCCheck.id.desc()).all()
    result = {}
    for row in rows:
        result.setdefault(row.check_type, row)
    return result


def readiness(db: Session) -> dict:
    def env(name): return bool((os.getenv(name) or "").strip())
    key_ok = False
    try:
        key_ok = len(_key()) == 32
    except Exception:
        pass
    dataset = db.query(BethelScreeningDataset).filter(BethelScreeningDataset.dataset_type == "sanctions", BethelScreeningDataset.active.is_(True)).order_by(BethelScreeningDataset.id.desc()).first()
    max_age = max(1, int(os.getenv("AML_DATASET_MAX_AGE_DAYS", "2")))
    sanctions_ready = bool(dataset and dataset.effective_date and 0 <= (date.today() - dataset.effective_date).days <= max_age)
    checks = {
        "encryption_key": key_ok,
        "private_storage": env("KYC_STORAGE_ROOT"),
        "malware_scanner": env("KYC_MALWARE_SCANNER_BASE_URL") and env("KYC_MALWARE_SCANNER_API_KEY"),
        "ocr_engine": env("KYC_OCR_BASE_URL") and env("KYC_OCR_API_KEY"),
        "document_authenticity_engine": env("KYC_AUTHENTICITY_VERIFIER_BASE_URL") and env("KYC_AUTHENTICITY_VERIFIER_API_KEY"),
        "biometric_engine": env("KYC_BIOMETRIC_VERIFIER_BASE_URL") and env("KYC_BIOMETRIC_VERIFIER_API_KEY"),
        "sanctions_data": sanctions_ready,
    }
    return {
        "ready_for_native_identity": all(checks.values()),
        "ready_for_native_cutover": all(checks.values()),
        "full_aml_ready": False,
        "aml_followup_required": True,
        "aml_followup_policy": "PEP and adverse-media gaps do not block Bethel identity verification; they remain Compliance follow-up items.",
        "checks": checks,
        "sanctions_dataset": {"ready": sanctions_ready, "dataset_id": dataset.id if dataset else None, "source": dataset.source_name if dataset else None, "age_days": (date.today() - dataset.effective_date).days if dataset and dataset.effective_date else None},
    }
