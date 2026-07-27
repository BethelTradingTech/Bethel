from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin, require_subscriber_or_admin
from api.copytrading.models import CopySubscriber
from api.database import get_db
from api.legal.models import LegalAcceptance, LegalDocument
from api.legal.service import (
    acceptance_status,
    all_current_accepted,
    current_documents,
)
from api.onboarding.models import ClientOnboarding
from api.onboarding.service import recompute_activation


router = APIRouter(tags=["Legal Consent"])


class ConsentRequest(BaseModel):
    accepted: bool
    document_ids: list[int] = Field(min_length=1)


class PublishDocument(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    version: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=100)


@router.get("/legal/documents")
def legal_documents(db: Session = Depends(get_db)):
    return {
        "status": "success",
        "documents": [
            {
                "id": row.id,
                "code": row.code,
                "version": row.version,
                "title": row.title,
                "content": row.content,
                "content_hash": row.content_hash,
                "effective_at": row.effective_at.isoformat(),
            }
            for row in current_documents(db)
        ],
    }


@router.get("/legal/{subscriber_id}/status")
def legal_status(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    rows = acceptance_status(db, subscriber_id)
    return {
        "subscriber_id": subscriber_id,
        "complete": bool(rows) and all(row["accepted"] for row in rows),
        "documents": rows,
    }


@router.post("/legal/{subscriber_id}/accept")
def accept_documents(
    subscriber_id: int,
    data: ConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    _actor=Depends(require_subscriber_or_admin),
):
    if not data.accepted:
        raise HTTPException(status_code=422, detail="Explicit legal consent is required")
    subscriber = (
        db.query(CopySubscriber)
        .filter(CopySubscriber.id == subscriber_id)
        .first()
    )
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    documents = current_documents(db)
    current_ids = {row.id for row in documents}
    if set(data.document_ids) != current_ids:
        raise HTTPException(
            status_code=409,
            detail="Every current legal document must be accepted together",
        )
    now = datetime.utcnow()
    for document in documents:
        exists = (
            db.query(LegalAcceptance)
            .filter(
                LegalAcceptance.subscriber_id == subscriber_id,
                LegalAcceptance.document_id == document.id,
            )
            .first()
        )
        if exists:
            continue
        db.add(LegalAcceptance(
            subscriber_id=subscriber_id,
            document_id=document.id,
            document_code=document.code,
            document_version=document.version,
            content_hash=document.content_hash,
            accepted_at=now,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        ))
    onboarding = (
        db.query(ClientOnboarding)
        .filter(ClientOnboarding.subscriber_id == subscriber_id)
        .first()
    )
    if onboarding:
        db.flush()
        recompute_activation(db, onboarding)
    db.commit()
    return {
        "status": "accepted",
        "accepted_at": now.isoformat(),
        "documents": acceptance_status(db, subscriber_id),
    }


@router.get("/admin/legal/acceptances")
def admin_acceptances(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    subscribers = {row.id: row for row in db.query(CopySubscriber).all()}
    rows = []
    for subscriber_id, subscriber in subscribers.items():
        status = acceptance_status(db, subscriber_id)
        rows.append({
            "subscriber_id": subscriber_id,
            "subscriber_name": subscriber.name,
            "subscriber_email": subscriber.email,
            "complete": bool(status) and all(row["accepted"] for row in status),
            "accepted_count": sum(1 for row in status if row["accepted"]),
            "required_count": len(status),
            "documents": status,
        })
    return {"status": "success", "subscribers": rows}


@router.post("/admin/legal/documents")
def publish_document(
    data: PublishDocument,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    code = data.code.strip().upper()
    version = data.version.strip()
    content = data.content.strip()
    duplicate = (
        db.query(LegalDocument)
        .filter(
            LegalDocument.code == code,
            LegalDocument.version == version,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Document version already exists")
    db.query(LegalDocument).filter(
        LegalDocument.code == code,
        LegalDocument.active.is_(True),
    ).update({"active": False}, synchronize_session=False)
    document = LegalDocument(
        code=code,
        version=version,
        title=data.title.strip(),
        content=content,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        active=True,
        effective_at=datetime.utcnow(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return {
        "status": "published",
        "id": document.id,
        "code": document.code,
        "version": document.version,
        "content_hash": document.content_hash,
        "message": "All subscribers must accept this new current version",
    }
