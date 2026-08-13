from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.kyc.native_engine import CheckResult, latest_checks, load_evidence, record_check
from api.kyc.native_models import BethelKYCEvidence, BethelKYCSession
from api.onboarding.service import get_or_create_onboarding, recompute_activation


router = APIRouter(prefix="/admin/kyc/native", tags=["Native KYC Compliance Review"])
EVIDENCE_CATEGORIES = {"document-front", "document-back", "selfie"}


class ComplianceDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=500)
    attestation: bool = False


def _latest_session(db: Session, subscriber_id: int) -> BethelKYCSession:
    item = (
        db.query(BethelKYCSession)
        .filter(BethelKYCSession.subscriber_id == subscriber_id)
        .order_by(BethelKYCSession.id.desc())
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="No Bethel Native KYC submission found")
    return item


def _reviewer_identity(actor: dict) -> str:
    value = actor.get("email") or actor.get("sub") or actor.get("username") or actor.get("role") or "admin"
    return str(value)[:160]


@router.get("/{subscriber_id}")
def get_native_kyc_review(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == subscriber_id).first()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    item = _latest_session(db, subscriber_id)
    checks = latest_checks(db, item.id)
    evidence = (
        db.query(BethelKYCEvidence)
        .filter(BethelKYCEvidence.session_id == item.id)
        .order_by(BethelKYCEvidence.id.asc())
        .all()
    )
    onboarding = get_or_create_onboarding(db, subscriber_id)

    return {
        "provider": "bethel_native",
        "subscriber": {
            "id": subscriber.id,
            "name": subscriber.name,
            "email": subscriber.email,
        },
        "session": {
            "reference": item.reference,
            "status": item.status,
            "decision": item.decision,
            "requires_manual_review": item.requires_manual_review,
            "review_reason": item.review_reason,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "completed_at": item.completed_at,
        },
        "identity": {
            "date_of_birth": item.date_of_birth,
            "nationality": item.nationality,
            "document_type": item.document_type,
            "issuing_country": item.issuing_country,
            "document_expiry": item.document_expiry,
            "document_number": "Not exposed by the review API",
        },
        "risk": {
            "sanctions_status": item.sanctions_status,
            "aml_followup_required": item.aml_followup_required,
            "liveness_score": item.liveness_score,
            "face_match_score": item.face_match_score,
        },
        "checks": {
            name: {
                "status": row.status,
                "score": row.score,
                "reasons": row.reasons or [],
                "engine_version": row.engine_version,
                "checked_at": row.checked_at,
            }
            for name, row in checks.items()
        },
        "evidence": [
            {
                "category": row.category,
                "content_type": row.content_type,
                "size_bytes": row.size_bytes,
                "sha256_prefix": row.sha256[:12],
                "created_at": row.created_at,
                "review_url": f"/admin/kyc/native/{subscriber_id}/evidence/{row.category}",
            }
            for row in evidence
            if row.category in EVIDENCE_CATEGORIES
        ],
        "onboarding": {
            "kyc_status": onboarding.kyc_status,
            "kyc_submitted_at": onboarding.kyc_submitted_at,
            "kyc_reviewed_at": onboarding.kyc_reviewed_at,
        },
    }


@router.get("/{subscriber_id}/evidence/{category}")
def get_native_kyc_evidence(
    subscriber_id: int,
    category: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if category not in EVIDENCE_CATEGORIES:
        raise HTTPException(status_code=404, detail="KYC evidence category not found")

    item = _latest_session(db, subscriber_id)
    row = (
        db.query(BethelKYCEvidence)
        .filter(
            BethelKYCEvidence.session_id == item.id,
            BethelKYCEvidence.subscriber_id == subscriber_id,
            BethelKYCEvidence.category == category,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="KYC evidence not found")

    try:
        content = load_evidence(subscriber_id, item.reference, row.category, row.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail="KYC evidence is no longer available in protected storage") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to decrypt KYC evidence") from exc

    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "application/pdf": "pdf",
    }.get(row.content_type, "bin")
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f'inline; filename="kyc-{category}.{extension}"',
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; sandbox",
    }
    return Response(content=content, media_type=row.content_type, headers=headers)


@router.post("/{subscriber_id}/decision")
def decide_native_kyc_review(
    subscriber_id: int,
    data: ComplianceDecision,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == subscriber_id).first()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    item = _latest_session(db, subscriber_id)
    onboarding = get_or_create_onboarding(db, subscriber_id)
    if onboarding.kyc_status != "PENDING" or item.status not in {"manual_review", "submitted", "pending"}:
        raise HTTPException(status_code=409, detail="Native KYC is not pending Compliance review")

    reason = (data.reason or "").strip()
    if data.decision == "APPROVED" and not data.attestation:
        raise HTTPException(status_code=422, detail="Compliance review attestation is required before approval")
    if data.decision == "REJECTED" and len(reason) < 3:
        raise HTTPException(status_code=422, detail="A rejection reason is required")

    now = datetime.now(timezone.utc)
    reviewer = _reviewer_identity(admin)
    if data.decision == "APPROVED":
        item.status = "approved"
        item.decision = "approved"
        item.requires_manual_review = False
        item.review_reason = reason or "Approved after manual Compliance review"
        item.completed_at = now
        onboarding.kyc_status = "APPROVED"
        onboarding.rejection_reason = None
        check_status = "passed"
        check_reasons = [item.review_reason]
    else:
        item.status = "rejected"
        item.decision = "rejected"
        item.requires_manual_review = False
        item.review_reason = reason
        item.completed_at = now
        onboarding.kyc_status = "REJECTED"
        onboarding.rejection_reason = reason
        check_status = "failed"
        check_reasons = [reason]

    onboarding.kyc_reviewed_at = datetime.utcnow()
    record_check(
        db,
        item,
        CheckResult(
            "compliance_review",
            check_status,
            reasons=check_reasons,
            evidence={
                "reviewer": reviewer,
                "decision": data.decision,
                "aml_followup_required": bool(item.aml_followup_required),
            },
        ),
        "bethel-native-compliance-review-v1",
    )
    recompute_activation(db, onboarding)
    db.commit()

    return {
        "subscriber_id": subscriber_id,
        "reference": item.reference,
        "decision": data.decision,
        "kyc_status": onboarding.kyc_status,
        "aml_followup_required": item.aml_followup_required,
        "reviewed_at": onboarding.kyc_reviewed_at,
    }
