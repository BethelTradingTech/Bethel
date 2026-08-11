from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint, func

from api.database import Base


class BethelKYCSession(Base):
    __tablename__ = "bethel_kyc_sessions"

    id = Column(Integer, primary_key=True)
    reference = Column(String(48), unique=True, nullable=False, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    status = Column(String(24), nullable=False, default="created", index=True)
    decision = Column(String(24), nullable=True, index=True)
    document_type = Column(String(32), nullable=True)
    issuing_country = Column(String(3), nullable=True)
    document_expiry = Column(Date, nullable=True)
    document_number_hash = Column(String(64), nullable=True, index=True)
    challenge_hash = Column(String(64), nullable=False)
    challenge_consumed_at = Column(DateTime(timezone=True), nullable=True)
    document_quality_score = Column(Float, nullable=True)
    liveness_score = Column(Float, nullable=True)
    face_match_score = Column(Float, nullable=True)
    sanctions_status = Column(String(24), nullable=False, default="not_screened")
    aml_followup_required = Column(Boolean, nullable=False, default=True)
    requires_manual_review = Column(Boolean, nullable=False, default=False)
    review_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class BethelKYCEvidence(Base):
    __tablename__ = "bethel_kyc_evidence"
    __table_args__ = (UniqueConstraint("session_id", "category", name="uq_bethel_kyc_evidence_category"),)

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=False, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    category = Column(String(32), nullable=False)
    storage_key = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False)
    content_type = Column(String(80), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BethelKYCCheck(Base):
    __tablename__ = "bethel_kyc_checks"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=False, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    check_type = Column(String(32), nullable=False, index=True)
    status = Column(String(24), nullable=False, index=True)
    score = Column(Float, nullable=True)
    reasons = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    engine_version = Column(String(80), nullable=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BethelScreeningDataset(Base):
    __tablename__ = "bethel_screening_datasets"

    id = Column(Integer, primary_key=True)
    dataset_type = Column(String(24), nullable=False, index=True)
    source_name = Column(String(160), nullable=False)
    source_url = Column(String(500), nullable=True)
    sha256 = Column(String(64), nullable=False)
    record_count = Column(Integer, nullable=False, default=0)
    effective_date = Column(Date, nullable=True)
    active = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BethelScreeningEntry(Base):
    __tablename__ = "bethel_screening_entries"
    __table_args__ = (UniqueConstraint("dataset_id", "entry_key", name="uq_bethel_screening_entry_key"),)

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, nullable=False, index=True)
    dataset_type = Column(String(24), nullable=False, index=True)
    entry_key = Column(String(128), nullable=False)
    primary_name = Column(String(240), nullable=False, index=True)
    aliases = Column(JSON, nullable=True)
    date_of_birth = Column(Date, nullable=True, index=True)
    nationality = Column(String(3), nullable=True)
    countries = Column(JSON, nullable=True)
    source_reference = Column(String(240), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
