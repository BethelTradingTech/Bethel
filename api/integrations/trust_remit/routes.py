import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.database import get_db
from api.integrations.trust_remit.models import TrustRemitIdentityLink
from api.integrations.trust_remit.security import verify_trust_remit_signature

router = APIRouter(
    prefix="/integrations/trust-remit",
    tags=["Trust & Remit Integration"],
    dependencies=[Depends(verify_trust_remit_signature)],
)


class IdentityLinkRequest(BaseModel):
    subject_type: str = Field(pattern=r"^(subscriber|investor)$")
    subject_id: int = Field(gt=0)


def serialize(link: TrustRemitIdentityLink) -> dict:
    return {
        "subject_type": link.bethel_subject_type,
        "subject_id": link.bethel_subject_id,
        "trust_remit_customer_reference": link.trust_remit_customer_reference,
        "status": link.status,
        "capabilities": {
            "wallet": link.wallet_enabled,
            "remittance": link.remittance_enabled,
            "crypto": link.crypto_enabled,
        },
    }


@router.post("/identity-links", status_code=201)
def create_identity_link(data: IdentityLinkRequest, db: Session = Depends(get_db)):
    existing = db.query(TrustRemitIdentityLink).filter(
        TrustRemitIdentityLink.bethel_subject_type == data.subject_type,
        TrustRemitIdentityLink.bethel_subject_id == data.subject_id,
    ).first()
    if existing:
        return {"created": False, "data": serialize(existing)}

    link = TrustRemitIdentityLink(
        bethel_subject_type=data.subject_type,
        bethel_subject_id=data.subject_id,
        trust_remit_customer_reference=f"TRC-{secrets.token_hex(12).upper()}",
        status="sandbox",
        wallet_enabled=False,
        remittance_enabled=False,
        crypto_enabled=False,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"created": True, "data": serialize(link)}


@router.get("/identity-links/{subject_type}/{subject_id}")
def get_identity_link(subject_type: str, subject_id: int, db: Session = Depends(get_db)):
    if subject_type not in {"subscriber", "investor"}:
        raise HTTPException(status_code=422, detail="Unsupported Bethel subject type")
    link = db.query(TrustRemitIdentityLink).filter(
        TrustRemitIdentityLink.bethel_subject_type == subject_type,
        TrustRemitIdentityLink.bethel_subject_id == subject_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Trust & Remit identity link not found")
    return {"data": serialize(link)}


@router.get("/capabilities")
def integration_capabilities():
    return {
        "mode": "sandbox",
        "identity_linking": True,
        "single_admin_system": False,
        "live_wallets": False,
        "live_remittances": False,
        "live_crypto": False,
        "btt": {"enabled": False, "planned_mode": "testnet_utility_rewards"},
    }
