from datetime import datetime
import hashlib

from sqlalchemy.orm import Session

from api.legal.models import LegalAcceptance, LegalDocument


DOCUMENT_SET_VERSION = "2026-07-26-v1"

DOCUMENTS = [
    {
        "code": "TERMS",
        "title": "Terms of Service",
        "content": """WORKING LEGAL TEMPLATE — COUNSEL REVIEW REQUIRED

Bethel Trading Technologies provides subscription-based trading technology, account connectivity, analytics and non-custodial copy-trading tools. Bethel does not accept deposits, hold subscriber money, control withdrawals, guarantee profits, or promise any investment return.

The subscriber must maintain an account with a broker chosen by the subscriber and remains responsible for that broker relationship, account funding, permissions, taxes, device security and compliance with applicable law. Service access may be suspended for non-payment, expired subscriptions, failed identity verification, security concerns, breach of these terms, regulatory requirements or technical risk.

Fees may include the selected subscription charge and the separately disclosed 20% performance fee on eligible realized net profit above the high-water mark. Fees, billing intervals and material changes must be displayed before acceptance. Trading results, service availability and execution are not guaranteed.

The service is provided on an as-available basis. To the extent permitted by law, Bethel is not responsible for broker failure, market interruption, slippage, rejected orders, internet loss, platform outages, third-party failure or losses inherent in trading. The subscriber may stop using the service and revoke account connectivity, subject to outstanding contractual obligations.
""",
    },
    {
        "code": "PRIVACY",
        "title": "Privacy Policy",
        "content": """WORKING LEGAL TEMPLATE — COUNSEL REVIEW REQUIRED

Bethel may process identity and contact information, KYC results, broker-account identifiers, onboarding records, payment references, subscription information, trading and performance data, security logs, device/browser information, IP address and consent evidence.

Information is used to provide and secure the service, verify identity and payments, connect authorized broker accounts, calculate performance and fees, prevent fraud, maintain records, communicate with subscribers and meet legal or regulatory duties. Appropriate data may be shared with contracted service providers such as identity-verification, payment, hosting, security and broker-integration providers.

Bethel does not sell subscriber personal information. Information is retained only as reasonably necessary for services, disputes, accounting, security and legal obligations. Cross-border processing may occur where service providers operate internationally. Subscribers may request access or correction and may ask about deletion where retention is not legally required.

Reasonable safeguards are used, but no system is completely secure. Privacy questions and rights requests should be sent through Bethel’s official contact channel published on its website.
""",
    },
    {
        "code": "RISK",
        "title": "Trading Risk Disclosure",
        "content": """WORKING LEGAL TEMPLATE — COUNSEL REVIEW REQUIRED

Foreign exchange, contracts for difference, leveraged products and algorithmic trading involve substantial risk. A subscriber may lose part or all of the money held with the subscriber’s broker, and losses may occur rapidly. Leverage magnifies both gains and losses.

Past, simulated, paper, demo, back-tested or third-party-verified performance does not guarantee future results. Statistics may differ because of deposits, withdrawals, pricing, spreads, commissions, swaps, latency, liquidity, broker rules, execution quality and account settings.

Copy trading cannot ensure identical execution. Orders may be delayed, rejected, partially filled, filled at different prices or not copied. Technical failures, internet interruptions, market gaps and broker outages can cause losses. Open positions can remain exposed when synchronization fails.

The subscriber should use only risk capital, assess personal objectives and financial circumstances, understand the broker’s terms and obtain independent financial, tax and legal advice where appropriate. Bethel’s technology does not constitute a guarantee or individualized promise of profit.
""",
    },
    {
        "code": "COPY_TRADING",
        "title": "Non-Custodial Copy-Trading Agreement",
        "content": """WORKING LEGAL TEMPLATE — COUNSEL REVIEW REQUIRED

The subscriber authorizes Bethel’s software to transmit or reproduce trading instructions in the subscriber’s separately held broker account after onboarding approval. The subscriber retains ownership and withdrawal control of that account. Bethel does not receive or custody the account balance.

The subscriber understands that copied positions may differ from the source account because of balance, margin, leverage, symbols, broker specifications, market conditions, latency, slippage, minimum volume, rejected orders and technical interruption. The subscriber remains responsible for monitoring the account and may request suspension or disconnect the service.

Copy trading begins only after identity, payment, broker connection, subscription, legal consent, profit-share acceptance and administrator approval requirements are satisfied. Access may stop when any requirement expires or is revoked.

No representation is made that the subscriber will receive the same trades, prices, profits or losses as a master or reference account. This agreement does not transfer ownership of subscriber assets to Bethel.
""",
    },
    {
        "code": "ELECTRONIC",
        "title": "Electronic Communications and Signature Consent",
        "content": """WORKING LEGAL TEMPLATE — COUNSEL REVIEW REQUIRED

The subscriber agrees to receive agreements, disclosures, statements, payment notices, subscription reminders, security notices and service communications electronically through the portal, website or verified contact information.

Selecting the acceptance checkbox and submitting consent constitutes an electronic signature and confirms that the subscriber had an opportunity to read and retain each displayed document. Bethel records the document code, version, cryptographic content hash, subscriber identifier, timestamp, IP address and browser information as evidence of acceptance.

The subscriber must maintain accurate contact information and access to a device capable of displaying electronic records. A request to withdraw electronic consent may affect the ability to use an online-only service and does not invalidate records accepted before withdrawal.
""",
    },
]


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def seed_legal_documents(db: Session):
    now = datetime.utcnow()
    for item in DOCUMENTS:
        exists = (
            db.query(LegalDocument)
            .filter(
                LegalDocument.code == item["code"],
                LegalDocument.version == DOCUMENT_SET_VERSION,
            )
            .first()
        )
        if exists:
            continue
        db.query(LegalDocument).filter(
            LegalDocument.code == item["code"],
            LegalDocument.active.is_(True),
        ).update({"active": False}, synchronize_session=False)
        db.add(LegalDocument(
            code=item["code"],
            version=DOCUMENT_SET_VERSION,
            title=item["title"],
            content=item["content"].strip(),
            content_hash=content_hash(item["content"].strip()),
            active=True,
            effective_at=now,
        ))
    db.flush()


def current_documents(db: Session):
    return (
        db.query(LegalDocument)
        .filter(LegalDocument.active.is_(True))
        .order_by(LegalDocument.code.asc())
        .all()
    )


def acceptance_status(db: Session, subscriber_id: int):
    documents = current_documents(db)
    accepted = {
        row.document_id: row
        for row in db.query(LegalAcceptance)
        .filter(LegalAcceptance.subscriber_id == subscriber_id)
        .all()
    }
    rows = []
    for document in documents:
        evidence = accepted.get(document.id)
        valid = bool(
            evidence
            and evidence.document_version == document.version
            and evidence.content_hash == document.content_hash
        )
        rows.append({
            "document_id": document.id,
            "code": document.code,
            "title": document.title,
            "version": document.version,
            "content_hash": document.content_hash,
            "accepted": valid,
            "accepted_at": evidence.accepted_at.isoformat() if valid else None,
        })
    return rows


def all_current_accepted(db: Session, subscriber_id: int) -> bool:
    rows = acceptance_status(db, subscriber_id)
    return bool(rows) and all(row["accepted"] for row in rows)
