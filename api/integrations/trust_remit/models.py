from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint, func

from api.database import Base


class TrustRemitIdentityLink(Base):
    __tablename__ = "trust_remit_identity_links"
    __table_args__ = (
        UniqueConstraint("bethel_subject_type", "bethel_subject_id", name="uq_trust_remit_bethel_subject"),
    )

    id = Column(Integer, primary_key=True)
    bethel_subject_type = Column(String(20), nullable=False, index=True)
    bethel_subject_id = Column(Integer, nullable=False, index=True)
    trust_remit_customer_reference = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="sandbox")
    wallet_enabled = Column(Boolean, nullable=False, default=False)
    remittance_enabled = Column(Boolean, nullable=False, default=False)
    crypto_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
