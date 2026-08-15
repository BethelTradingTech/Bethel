"""Moderated public visitor reviews and star ratings for Bethel.

This is a Bethel-hosted reviews feature and does not claim affiliation with
Trustpilot or any third-party review platform. Public endpoints expose only
approved reviews. Visitor email/IP data is never returned publicly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin
from api.database import Base, SessionLocal

router = APIRouter(tags=["Public Reviews"])


class VisitorReview(Base):
    __tablename__ = "visitor_reviews"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(80), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=False)
    email = Column(String(254), nullable=True)
    ip_hash = Column(String(64), nullable=False, index=True)
    approved = Column(Boolean, nullable=False, default=False, index=True)
    rejected = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    moderated_at = Column(DateTime(timezone=True), nullable=True)


class ReviewCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    rating: int = Field(ge=1, le=5)
    review: str = Field(min_length=3, max_length=800)
    email: str | None = Field(default=None, max_length=254)


class ReviewModeration(BaseModel):
    action: str


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _visitor_ip(request: Request) -> str:
    return (
        (request.headers.get("cf-connecting-ip") or "").strip()
        or (request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
        or (request.client.host if request.client else "unknown")
    )[:128]


def _hash_ip(request: Request) -> str:
    salt = os.getenv("REVIEW_HASH_SALT", "").strip()
    if not salt:
        raise HTTPException(status_code=503, detail="Reviews are temporarily unavailable")
    raw = f"{salt}:{_visitor_ip(request)}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _clean(value: str) -> str:
    return " ".join(value.replace("<", "").replace(">", "").split()).strip()


@router.get("/public/reviews")
def list_public_reviews(limit: int = 12, db: Session = Depends(_db)):
    limit = max(1, min(limit, 50))
    approved = (
        db.query(VisitorReview)
        .filter(VisitorReview.approved.is_(True), VisitorReview.rejected.is_(False))
        .order_by(VisitorReview.created_at.desc())
        .limit(limit)
        .all()
    )
    aggregate = (
        db.query(func.avg(VisitorReview.rating), func.count(VisitorReview.id))
        .filter(VisitorReview.approved.is_(True), VisitorReview.rejected.is_(False))
        .first()
    )
    average = float(aggregate[0]) if aggregate and aggregate[0] is not None else 0.0
    count = int(aggregate[1]) if aggregate else 0
    return {
        "average_rating": round(average, 2),
        "review_count": count,
        "reviews": [
            {
                "id": row.id,
                "display_name": row.display_name,
                "rating": row.rating,
                "review": row.review_text,
                "created_at": row.created_at,
            }
            for row in approved
        ],
    }


@router.post("/public/reviews", status_code=202)
def submit_public_review(data: ReviewCreate, request: Request, db: Session = Depends(_db)):
    ip_hash = _hash_ip(request)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = (
        db.query(VisitorReview)
        .filter(VisitorReview.ip_hash == ip_hash, VisitorReview.created_at >= cutoff)
        .first()
    )
    if recent:
        raise HTTPException(status_code=429, detail="Only one review may be submitted per visitor every 24 hours")

    name = _clean(data.display_name)
    review = _clean(data.review)
    if len(name) < 2 or len(review) < 3:
        raise HTTPException(status_code=422, detail="Please provide a valid name and review")

    row = VisitorReview(
        display_name=name,
        rating=data.rating,
        review_text=review,
        email=(data.email or "").strip().lower() or None,
        ip_hash=ip_hash,
        approved=False,
        rejected=False,
    )
    db.add(row)
    db.commit()
    return {
        "status": "submitted",
        "message": "Thank you. Your review was received and will appear after moderation.",
    }


@router.get("/admin/reviews")
def admin_reviews(status: str = "pending", _=Depends(require_admin), db: Session = Depends(_db)):
    query = db.query(VisitorReview).order_by(VisitorReview.created_at.desc())
    if status == "pending":
        query = query.filter(VisitorReview.approved.is_(False), VisitorReview.rejected.is_(False))
    elif status == "approved":
        query = query.filter(VisitorReview.approved.is_(True), VisitorReview.rejected.is_(False))
    elif status == "rejected":
        query = query.filter(VisitorReview.rejected.is_(True))
    rows = query.limit(200).all()
    return {
        "reviews": [
            {
                "id": row.id,
                "display_name": row.display_name,
                "rating": row.rating,
                "review": row.review_text,
                "email": row.email,
                "approved": row.approved,
                "rejected": row.rejected,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/admin/reviews/{review_id}/moderate")
def moderate_review(review_id: int, data: ReviewModeration, _=Depends(require_admin), db: Session = Depends(_db)):
    row = db.query(VisitorReview).filter(VisitorReview.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    action = data.action.strip().lower()
    if action == "approve":
        row.approved = True
        row.rejected = False
    elif action == "reject":
        row.approved = False
        row.rejected = True
    else:
        raise HTTPException(status_code=422, detail="Action must be approve or reject")
    row.moderated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": action, "review_id": row.id}
