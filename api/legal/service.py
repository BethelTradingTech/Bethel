from datetime import datetime
import hashlib

from sqlalchemy.orm import Session

from api.legal.models import LegalAcceptance, LegalDocument


DOCUMENT_SET_VERSION = "2026-08-16-global-v2"
LEGACY_DOCUMENT_SET_VERSION = "2026-07-26-v1"

DOCUMENTS = [
    {
        "code": "TERMS",
        "title": "Global Terms of Service",
        "content": """Bethel Trading Technologies provides technology services that may include trading-account connectivity, analytics, monitoring, automation-support infrastructure and other software-enabled services made available from time to time. Services are offered through the applicable Bethel entity, partner or authorized arrangement and remain subject to eligibility, service availability and the laws and regulatory requirements applicable to the customer, service and jurisdiction.

Bethel does not guarantee profits, investment returns, trading outcomes, uninterrupted availability or identical execution between accounts. Unless a separately executed agreement expressly provides otherwise, Bethel does not accept customer trading deposits, custody customer brokerage assets or control customer withdrawals. A customer remains responsible for the customer's broker relationship, account funding, account permissions, taxes, credentials, device security and compliance with applicable law.

Access may be restricted, suspended or terminated where required for non-payment, expired subscription, failed or incomplete identity/compliance checks, security concerns, misuse, breach of these Terms, third-party or broker restrictions, regulatory requirements, sanctions controls or material technical risk. Services that require an authorization, licence, registration, partnership or regulatory approval may be unavailable in a jurisdiction until the applicable requirement is satisfied.

Bethel operates a subscription-first commercial model. The customer pays the price of the selected subscription or commercial plan and, where displayed at checkout, a separate one-time activation fee. Bethel does not charge a customer performance fee or profit-share under the standard subscription-first launch model unless a future service is expressly offered under a separate written agreement that the customer affirmatively accepts before any such fee becomes applicable. Current prices, billing intervals, discounts and applicable activation charges must be displayed before payment.

The service is provided on an as-available basis. To the maximum extent permitted by applicable law, Bethel is not responsible for losses caused by market movement, broker failure, slippage, rejected or delayed orders, spreads, swaps, commissions, liquidity conditions, outages, internet loss, third-party failures, customer configuration or other risks inherent in trading and technology services.

These Terms are intended as a global core agreement. Mandatory consumer, financial-services, privacy, electronic-commerce and other legal rights applicable in the customer's jurisdiction are not waived. Where a jurisdiction-specific schedule or serving-entity agreement applies, that schedule or agreement supplements these Terms and controls to the extent required by applicable law.
""",
    },
    {
        "code": "FEES",
        "title": "Fees, Activation and Promotions Policy",
        "content": """Bethel's commercial charges are controlled through the platform's current pricing records and may include recurring subscription charges, one-time charges, enterprise or custom charges, and approved promotional discounts. The amount shown in the customer's checkout or payment instruction at the time of payment is the operative amount for that transaction, subject to correction of obvious technical or pricing errors before service activation.

A one-time activation fee may apply to a customer's first paid activation. The activation fee is separate from the recurring subscription charge and is charged only when the platform indicates that it remains due. After a successful qualifying first payment has been confirmed, the normal recurring subscription charge does not include the one-time activation fee unless a new activation is expressly required under a separate agreement.

Promotional codes may apply to the activation fee, any eligible subscription, or a specifically selected plan. Promotions may be limited by customer, date, number of uses, currency, service, plan or other disclosed conditions. A promotion cannot be applied outside the scope assigned to that code. Bethel may deactivate a promotion prospectively, but a completed payment will be recorded according to the terms actually applied to that transaction.

Subscription renewals, grace periods, cancellation, suspension and reactivation are governed by the applicable plan and the terms displayed to the customer. Cancellation stops future recurring billing where recurring billing is enabled, but does not automatically reverse a completed charge or eliminate amounts already due. Refunds, reversals and charge disputes are handled according to applicable law, the payment provider's rules and any refund terms presented for the relevant service.

Customer trading capital is distinct from Bethel service fees. Unless expressly disclosed under a separately authorized service, trading capital is funded to and held with the customer's broker or other third-party financial provider and is not an activation fee or subscription payment to Bethel.
""",
    },
    {
        "code": "PRIVACY",
        "title": "Global Privacy Policy",
        "content": """Bethel may process identity and contact information, KYC and compliance results, broker-account identifiers, onboarding records, payment references, subscription information, trading and performance data, security logs, device/browser information, IP address and consent evidence.

Information is used to provide and secure the service, verify identity and payments, connect authorized accounts, administer subscriptions and promotions, prevent fraud, maintain records, communicate with customers and meet legal or regulatory duties. Appropriate information may be shared with contracted service providers such as identity-verification, payment, hosting, cybersecurity and broker-integration providers where necessary for these purposes.

Bethel does not sell customer personal information. Information is retained for as long as reasonably necessary for service delivery, security, accounting, dispute resolution and legal or regulatory obligations. Cross-border processing may occur because Bethel and its service providers may operate in multiple countries. Where applicable law requires additional safeguards or local rights, those requirements apply.

Customers may request access or correction and may ask about deletion, restriction, objection or portability where such rights exist and retention is not legally required. Reasonable administrative, technical and organizational safeguards are used, but no system can guarantee absolute security. Privacy requests should be made through Bethel's official contact channel.
""",
    },
    {
        "code": "RISK",
        "title": "Trading and Technology Risk Disclosure",
        "content": """Foreign exchange, contracts for difference, leveraged products, algorithmic trading and related financial-market activity involve substantial risk. A customer may lose part or all of the funds held with the customer's broker, and losses may occur rapidly. Leverage magnifies both gains and losses.

Past, simulated, paper, demo, back-tested, third-party-verified or otherwise presented performance does not guarantee future results. Statistics and realized outcomes may differ because of deposits, withdrawals, pricing, spreads, commissions, swaps, latency, liquidity, broker rules, execution quality, account settings and market conditions.

Account connectivity or copying technology cannot ensure identical execution. Orders may be delayed, rejected, partially filled, filled at different prices or not reproduced. Technical failures, internet interruptions, market gaps, third-party outages and broker outages can cause losses or leave positions exposed.

Customers should use only risk capital they can afford to lose, assess their own objectives and financial circumstances, understand their broker's terms and obtain independent financial, tax and legal advice where appropriate. Bethel's technology, analytics and communications are not a guarantee or individualized promise of profit.
""",
    },
    {
        "code": "ACCOUNT_CONNECTIVITY",
        "title": "Non-Custodial Account Connectivity Agreement",
        "content": """Where Bethel provides account-connectivity or trade-replication technology, the customer authorizes the relevant software components to connect to or interact with the customer's separately held broker account only within the permissions and service scope displayed to the customer. The customer retains ownership of the account and, subject to the broker's rules, control of deposits and withdrawals. Bethel does not obtain ownership of customer brokerage assets through this agreement.

Execution may differ from any source, model or reference account because of balance, margin, leverage, symbols, broker specifications, market conditions, latency, slippage, minimum volume, rejected orders and technical interruption. The customer remains responsible for monitoring the account and may disconnect or request suspension subject to security procedures and outstanding contractual obligations.

Service activation requires satisfaction of the applicable onboarding gates, which may include an active subscription, required payment including any applicable activation fee, identity/compliance approval, eligible broker connection, current legal consent and administrator approval. No separate performance-fee or profit-share acceptance is required under the standard subscription-first launch model.

No representation is made that a customer will receive the same trades, prices, profits or losses as another account. Nothing in this agreement transfers title to customer assets to Bethel.
""",
    },
    {
        "code": "ELECTRONIC",
        "title": "Electronic Communications and Signature Consent",
        "content": """The customer agrees to receive agreements, disclosures, statements, payment notices, subscription reminders, security notices and service communications electronically through the portal, website or verified contact information.

Selecting the acceptance control and submitting consent constitutes an electronic signature and confirms that the customer had an opportunity to read and retain each displayed document. Bethel records the document code, version, cryptographic content hash, customer identifier, timestamp, IP address and browser information as evidence of acceptance.

The customer must maintain accurate contact information and access to a device capable of displaying electronic records. Withdrawal of electronic consent may affect the ability to use an online-only service and does not invalidate records accepted before withdrawal, subject to applicable law.
""",
    },
]


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def seed_legal_documents(db: Session):
    now = datetime.utcnow()
    # Retire the complete legacy launch set, including the old COPY_TRADING
    # document whose code was replaced by ACCOUNT_CONNECTIVITY in Global v2.
    db.query(LegalDocument).filter(
        LegalDocument.version == LEGACY_DOCUMENT_SET_VERSION,
        LegalDocument.active.is_(True),
    ).update({"active": False}, synchronize_session=False)

    for item in DOCUMENTS:
        exists = (
            db.query(LegalDocument)
            .filter(LegalDocument.code == item["code"], LegalDocument.version == DOCUMENT_SET_VERSION)
            .first()
        )
        if exists:
            if not exists.active:
                exists.active = True
            continue
        db.query(LegalDocument).filter(
            LegalDocument.code == item["code"], LegalDocument.active.is_(True)
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
    return db.query(LegalDocument).filter(LegalDocument.active.is_(True)).order_by(LegalDocument.code.asc()).all()


def acceptance_status(db: Session, subscriber_id: int):
    documents = current_documents(db)
    accepted = {row.document_id: row for row in db.query(LegalAcceptance).filter(LegalAcceptance.subscriber_id == subscriber_id).all()}
    rows = []
    for document in documents:
        evidence = accepted.get(document.id)
        valid = bool(evidence and evidence.document_version == document.version and evidence.content_hash == document.content_hash)
        rows.append({"document_id": document.id, "code": document.code, "title": document.title, "version": document.version, "content_hash": document.content_hash, "accepted": valid, "accepted_at": evidence.accepted_at.isoformat() if valid else None})
    return rows


def all_current_accepted(db: Session, subscriber_id: int) -> bool:
    rows = acceptance_status(db, subscriber_id)
    return bool(rows) and all(row["accepted"] for row in rows)
