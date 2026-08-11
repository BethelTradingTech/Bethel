import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from api.auth.dependency import require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.kyc.sumsub import generate_sdk_token, verify_webhook
from api.onboarding.models import ClientOnboarding
from api.onboarding.service import get_or_create_onboarding, recompute_activation


router = APIRouter(prefix="/kyc", tags=["KYC"])


def _native_selected() -> bool:
    return (os.getenv("IDENTITY_VERIFICATION_MODE") or "sumsub").strip().lower() == "native"


@router.post("/{subscriber_id}/access-token")
def create_access_token(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    if _native_selected():
        raise HTTPException(status_code=410, detail="Sumsub is disabled. Bethel native identity verification is active.")
    subscriber = db.query(CopySubscriber).filter(CopySubscriber.id == subscriber_id).first()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    external_user_id = f"bethel-subscriber-{subscriber_id}"
    result = generate_sdk_token(external_user_id, subscriber.email)
    token = result.get("token")
    if not token:
        raise HTTPException(status_code=502, detail="Sumsub returned no SDK token")

    onboarding = get_or_create_onboarding(db, subscriber_id)
    onboarding.kyc_status = "PENDING"
    onboarding.kyc_submitted_at = onboarding.kyc_submitted_at or datetime.utcnow()
    onboarding.rejection_reason = None
    onboarding.admin_approval = "PENDING"
    recompute_activation(db, onboarding)
    db.commit()
    return {"token": token, "external_user_id": external_user_id, "expires_in": 600}


@router.post("/webhook/sumsub")
async def sumsub_webhook(
    request: Request,
    x_payload_digest: str = Header(default=""),
    x_payload_digest_alg: str = Header(default="HMAC_SHA256_HEX"),
    db: Session = Depends(get_db),
):
    if _native_selected():
        return {"received": True, "updated": False, "provider": "disabled_by_native_cutover"}
    raw_body = await request.body()
    verify_webhook(raw_body, x_payload_digest, x_payload_digest_alg)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON") from error

    if payload.get("type") != "applicantReviewed":
        return {"received": True, "updated": False}

    external_user_id = str(payload.get("externalUserId") or "")
    prefix = "bethel-subscriber-"
    if not external_user_id.startswith(prefix):
        return {"received": True, "updated": False}
    try:
        subscriber_id = int(external_user_id[len(prefix):])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid external user ID")

    onboarding = db.query(ClientOnboarding).filter(ClientOnboarding.subscriber_id == subscriber_id).first()
    if onboarding is None:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    review_result = payload.get("reviewResult") or {}
    answer = str(review_result.get("reviewAnswer") or "").upper()
    onboarding.kyc_reviewed_at = datetime.utcnow()
    if answer == "GREEN":
        onboarding.kyc_status = "APPROVED"
        onboarding.rejection_reason = None
    elif answer == "RED":
        onboarding.kyc_status = "REJECTED"
        labels = review_result.get("rejectLabels") or []
        onboarding.rejection_reason = ", ".join(map(str, labels)) or "KYC rejected"
        onboarding.admin_approval = "PENDING"
    else:
        onboarding.kyc_status = "PENDING"

    recompute_activation(db, onboarding)
    db.commit()
    return {"received": True, "updated": True, "kyc_status": onboarding.kyc_status}
