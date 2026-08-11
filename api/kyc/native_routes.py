import base64
import hashlib
import os
import secrets
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.auth.dependency import require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.kyc.native_engine import CheckResult, latest_checks, load_evidence, readiness, record_check, sanctions_check, store_evidence, _service
from api.kyc.native_models import BethelKYCCheck, BethelKYCEvidence, BethelKYCSession
from api.onboarding.service import get_or_create_onboarding, recompute_activation


router = APIRouter(prefix="/kyc", tags=["Bethel Native KYC"])
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_UPLOAD = int(os.getenv("KYC_MAX_UPLOAD_BYTES", "12582912"))


def _native_selected() -> bool:
    return (os.getenv("IDENTITY_VERIFICATION_MODE") or "sumsub").strip().lower() == "native"


def _session(db: Session, subscriber_id: int) -> BethelKYCSession:
    item = db.query(BethelKYCSession).filter(BethelKYCSession.subscriber_id == subscriber_id).order_by(BethelKYCSession.id.desc()).first()
    if item is None or item.status in {"approved", "rejected"}:
        challenge = secrets.token_urlsafe(32)
        item = BethelKYCSession(reference=f"BKL-{secrets.token_hex(12).upper()}", subscriber_id=subscriber_id, challenge_hash=hashlib.sha256(challenge.encode()).hexdigest())
        db.add(item)
        db.flush()
        item._plain_challenge = challenge
    return item


def _put_evidence(db: Session, item: BethelKYCSession, category: str, upload: UploadFile, data: bytes):
    existing = db.query(BethelKYCEvidence).filter(BethelKYCEvidence.session_id == item.id, BethelKYCEvidence.category == category).first()
    storage_key, digest = store_evidence(item.subscriber_id, item.reference, category, data)
    if existing:
        existing.storage_key, existing.sha256, existing.content_type, existing.size_bytes = storage_key, digest, upload.content_type or "application/octet-stream", len(data)
        return existing
    evidence = BethelKYCEvidence(session_id=item.id, subscriber_id=item.subscriber_id, category=category, storage_key=storage_key, sha256=digest, content_type=upload.content_type or "application/octet-stream", size_bytes=len(data))
    db.add(evidence)
    return evidence


@router.get("/native/readiness")
def native_readiness(db: Session = Depends(get_db)):
    state = readiness(db)
    return {"provider": "bethel_native", "selected": _native_selected(), **state}


@router.post("/{subscriber_id}/native/session")
def create_native_session(subscriber_id: int, db: Session = Depends(get_db), _actor=Depends(require_subscriber_or_admin)):
    if not _native_selected():
        raise HTTPException(status_code=409, detail="Bethel native KYC is not selected")
    state = readiness(db)
    if not state["ready_for_native_identity"]:
        raise HTTPException(status_code=503, detail={"message": "Bethel native KYC is not production-ready", "native_kyc": state})
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == subscriber_id).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    item = _session(db, subscriber_id)
    challenge = getattr(item, "_plain_challenge", None)
    if challenge is None:
        challenge = secrets.token_urlsafe(32)
        item.challenge_hash = hashlib.sha256(challenge.encode()).hexdigest()
        item.challenge_consumed_at = None
    onboarding = get_or_create_onboarding(db, subscriber_id)
    onboarding.kyc_status = "PENDING"
    onboarding.kyc_submitted_at = onboarding.kyc_submitted_at or datetime.utcnow()
    onboarding.rejection_reason = None
    recompute_activation(db, onboarding)
    db.commit()
    return {"reference": item.reference, "challenge": challenge, "status": item.status, "provider": "bethel_native"}


async def _read_upload(upload: UploadFile, label: str, allow_pdf: bool = True) -> bytes:
    content_type = upload.content_type or ""
    allowed = ALLOWED_CONTENT_TYPES if allow_pdf else ALLOWED_CONTENT_TYPES - {"application/pdf"}
    if content_type not in allowed:
        raise HTTPException(status_code=422, detail=f"{label} must be JPEG, PNG, WebP" + (" or PDF" if allow_pdf else ""))
    data = await upload.read()
    if not data or len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail=f"{label} is empty or exceeds the upload limit")
    return data


@router.post("/{subscriber_id}/native/submit")
async def submit_native_kyc(
    subscriber_id: int,
    reference: str = Form(...),
    challenge: str = Form(...),
    document_type: str = Form(...),
    issuing_country: str = Form(...),
    document_number: str = Form(...),
    document_expiry: date = Form(...),
    document_front: UploadFile = File(...),
    selfie: UploadFile = File(...),
    document_back: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    if not _native_selected():
        raise HTTPException(status_code=409, detail="Bethel native KYC is not selected")
    state = readiness(db)
    if not state["ready_for_native_identity"]:
        raise HTTPException(status_code=503, detail={"message": "Bethel native KYC is not production-ready", "native_kyc": state})
    item = db.query(BethelKYCSession).filter(BethelKYCSession.reference == reference, BethelKYCSession.subscriber_id == subscriber_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Native KYC session not found")
    if item.challenge_consumed_at is not None or not secrets.compare_digest(item.challenge_hash, hashlib.sha256(challenge.encode()).hexdigest()):
        raise HTTPException(status_code=409, detail="Biometric challenge is invalid or already used")
    if document_expiry <= date.today():
        raise HTTPException(status_code=422, detail="Identity document is expired")
    country = issuing_country.strip().upper()
    if len(country) != 3:
        raise HTTPException(status_code=422, detail="Issuing country must be a 3-letter country code")

    front_data = await _read_upload(document_front, "Document front")
    selfie_data = await _read_upload(selfie, "Selfie", allow_pdf=False)
    back_data = await _read_upload(document_back, "Document back") if document_back else None

    item.document_type = document_type.strip().lower()
    item.issuing_country = country
    item.document_expiry = document_expiry
    item.document_number_hash = hashlib.sha256(document_number.strip().upper().encode()).hexdigest()
    item.challenge_consumed_at = datetime.now(timezone.utc)
    front = _put_evidence(db, item, "document-front", document_front, front_data)
    selfie_row = _put_evidence(db, item, "selfie", selfie, selfie_data)
    back = _put_evidence(db, item, "document-back", document_back, back_data) if document_back and back_data else None
    db.flush()

    common = {"session_reference": item.reference, "document_type": item.document_type, "issuing_country": item.issuing_country}
    malware_results = []
    for category, row, raw in (("document-front", front, front_data), ("document-back", back, back_data)):
        if row is None or raw is None:
            continue
        malware_results.append(_service("KYC_MALWARE_SCANNER_BASE_URL", "KYC_MALWARE_SCANNER_API_KEY", "/scan", {"session_reference": item.reference, "file_b64": base64.b64encode(raw).decode(), "sha256": row.sha256, "content_type": row.content_type}, "malware", 60))
    malware = CheckResult("malware", "passed" if malware_results and all(x.status == "passed" for x in malware_results) else "failed" if any(x.status == "failed" for x in malware_results) else "not_available", 100.0 if malware_results and all(x.status == "passed" for x in malware_results) else None, [reason for result in malware_results for reason in result.reasons])
    record_check(db, item, malware, "bethel-native-malware-v1")

    authenticity = _service("KYC_AUTHENTICITY_VERIFIER_BASE_URL", "KYC_AUTHENTICITY_VERIFIER_API_KEY", "/verify-authenticity", {**common, "front_image_b64": base64.b64encode(front_data).decode(), "back_image_b64": base64.b64encode(back_data).decode() if back_data else None}, "authenticity", 120)
    record_check(db, item, authenticity, "bethel-native-authenticity-v1")

    ocr = _service("KYC_OCR_BASE_URL", "KYC_OCR_API_KEY", "/extract-identity", {**common, "front_image_b64": base64.b64encode(front_data).decode(), "front_content_type": front.content_type, "back_image_b64": base64.b64encode(back_data).decode() if back_data else None, "back_content_type": back.content_type if back else None}, "ocr", 120)
    record_check(db, item, ocr, "bethel-native-ocr-v1")

    liveness = _service("KYC_BIOMETRIC_VERIFIER_BASE_URL", "KYC_BIOMETRIC_VERIFIER_API_KEY", "/verify-liveness", {"session_reference": item.reference, "selfie_image_b64": base64.b64encode(selfie_data).decode(), "selfie_sha256": selfie_row.sha256, "method": "challenge_bound_passive"}, "liveness", 120)
    face = _service("KYC_BIOMETRIC_VERIFIER_BASE_URL", "KYC_BIOMETRIC_VERIFIER_API_KEY", "/compare-face", {"session_reference": item.reference, "selfie_image_b64": base64.b64encode(selfie_data).decode(), "selfie_sha256": selfie_row.sha256, "document_image_b64": base64.b64encode(front_data).decode()}, "face_match", 120)
    record_check(db, item, liveness, "bethel-native-biometric-v1")
    record_check(db, item, face, "bethel-native-biometric-v1")
    item.liveness_score, item.face_match_score = liveness.score, face.score

    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == subscriber_id).first()
    sanctions = sanctions_check(db, subscriber.name if subscriber else "", None)
    record_check(db, item, sanctions, "bethel-native-sanctions-v1")
    item.sanctions_status = "clear" if sanctions.status == "passed" else "potential_match" if sanctions.status == "review" else "not_screened"

    core = {x.check_type: x for x in (malware, authenticity, ocr, liveness, face, sanctions)}
    hard_fail = any(core[name].status == "failed" for name in {"malware", "authenticity", "liveness", "face_match"})
    all_pass = all(result.status == "passed" for result in core.values())
    onboarding = get_or_create_onboarding(db, subscriber_id)
    onboarding.kyc_reviewed_at = datetime.utcnow()
    if hard_fail:
        item.status = item.decision = "rejected"
        item.requires_manual_review = False
        item.review_reason = "One or more identity-security checks failed"
        onboarding.kyc_status = "REJECTED"
        onboarding.rejection_reason = item.review_reason
    elif all_pass:
        item.status = item.decision = "approved"
        item.completed_at = datetime.now(timezone.utc)
        item.requires_manual_review = False
        item.review_reason = None
        onboarding.kyc_status = "APPROVED"
        onboarding.rejection_reason = None
    else:
        item.status = item.decision = "manual_review"
        item.requires_manual_review = True
        item.review_reason = "One or more native identity checks require Compliance review"
        onboarding.kyc_status = "PENDING"
        onboarding.rejection_reason = item.review_reason
    recompute_activation(db, onboarding)
    db.commit()
    return {"provider": "bethel_native", "reference": item.reference, "decision": item.decision, "kyc_status": onboarding.kyc_status, "aml_followup_required": True, "checks": {name: {"status": result.status, "score": result.score, "reasons": result.reasons} for name, result in core.items()}}


@router.get("/{subscriber_id}/native/status")
def native_status(subscriber_id: int, db: Session = Depends(get_db), _actor=Depends(require_subscriber_or_admin)):
    item = db.query(BethelKYCSession).filter(BethelKYCSession.subscriber_id == subscriber_id).order_by(BethelKYCSession.id.desc()).first()
    if not item:
        return {"provider": "bethel_native", "status": "NOT_STARTED", "aml_followup_required": True}
    checks = latest_checks(db, item.id)
    return {"provider": "bethel_native", "reference": item.reference, "status": item.status, "decision": item.decision, "sanctions_status": item.sanctions_status, "aml_followup_required": item.aml_followup_required, "requires_manual_review": item.requires_manual_review, "review_reason": item.review_reason, "checks": {name: {"status": row.status, "score": row.score, "reasons": row.reasons or []} for name, row in checks.items()}}
