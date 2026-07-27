from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint

from api.database import Base


class LegalDocument(Base):
    __tablename__ = "legal_documents"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_legal_document_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, index=True)
    version = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    active = Column(Boolean, nullable=False, default=True, index=True)
    effective_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class LegalAcceptance(Base):
    __tablename__ = "legal_acceptances"
    __table_args__ = (
        UniqueConstraint(
            "subscriber_id",
            "document_id",
            name="uq_subscriber_legal_acceptance",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, nullable=False, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    document_code = Column(String(50), nullable=False)
    document_version = Column(String(40), nullable=False)
    content_hash = Column(String(64), nullable=False)
    accepted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(String(80), nullable=True)
    user_agent = Column(String(500), nullable=True)
