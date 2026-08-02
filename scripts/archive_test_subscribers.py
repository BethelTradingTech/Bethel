"""Archive every non-owner subscriber while preserving immutable audit history.

This removes test/demo subscribers from active operation without deleting
payment, compliance, or security evidence.
"""

from datetime import datetime
import sys

from api.broker_accounts.models import BrokerAccount
from api.copytrading.models import CopySubscriber
from api.database import SessionLocal
from api.onboarding.models import ClientOnboarding
from api.subscription_lifecycle.models import SubscriptionAudit, SubscriptionLifecycle


PROTECTED_FOLLOWER_LOGIN = "49224282"


def main() -> int:
    db = SessionLocal()
    try:
        protected = db.query(BrokerAccount).filter(
            BrokerAccount.login == PROTECTED_FOLLOWER_LOGIN,
            BrokerAccount.status != "ARCHIVED",
        ).first()
        if protected is None:
            print(
                "Stopped: protected follower account 49224282 must be linked "
                "and active before cleanup."
            )
            return 1

        subscribers = db.query(CopySubscriber).order_by(CopySubscriber.id).all()
        print("Subscriber audit:")
        for row in subscribers:
            accounts = db.query(BrokerAccount).filter(
                BrokerAccount.subscriber_id == row.id
            ).all()
            logins = ", ".join(account.login for account in accounts) or "none"
            marker = "KEEP" if row.id == protected.subscriber_id else "ARCHIVE"
            print(f"  [{marker}] id={row.id} email={row.email} broker_logins={logins}")

        phrase = f"ARCHIVE ALL EXCEPT {PROTECTED_FOLLOWER_LOGIN}"
        if input(f"Type {phrase}: ").strip() != phrase:
            print("Cancelled. No records changed.")
            return 1

        archived = 0
        for subscriber in subscribers:
            if subscriber.id == protected.subscriber_id:
                continue
            subscriber.status = "ARCHIVED"
            subscriber.synchronized = False
            archived += 1

            for account in db.query(BrokerAccount).filter(
                BrokerAccount.subscriber_id == subscriber.id
            ).all():
                account.status = "ARCHIVED"
                account.execution_mode = "PAPER"
                account.live_authorized = False
                account.live_authorized_at = None
                account.live_authorized_by = None

            onboarding = db.query(ClientOnboarding).filter(
                ClientOnboarding.subscriber_id == subscriber.id
            ).first()
            if onboarding is not None:
                onboarding.subscription_status = "SUSPENDED"
                onboarding.copy_trading_status = "INACTIVE"
                onboarding.admin_approval = "ARCHIVED"

            lifecycle = db.query(SubscriptionLifecycle).filter(
                SubscriptionLifecycle.subscriber_id == subscriber.id
            ).first()
            if lifecycle is not None:
                previous = lifecycle.status
                lifecycle.status = "SUSPENDED"
                lifecycle.manual_suspended = True
                lifecycle.suspended_at = datetime.utcnow()
                db.add(SubscriptionAudit(
                    subscriber_id=subscriber.id,
                    action="ARCHIVE_TEST",
                    previous_status=previous,
                    new_status="SUSPENDED",
                    reference=lifecycle.last_payment_reference,
                    administrator="SUPER_ADMIN_CLEANUP",
                ))

        db.commit()
        print(f"Archived {archived} non-owner subscriber account(s).")
        print(f"Protected follower account: {PROTECTED_FOLLOWER_LOGIN}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Cleanup failed; no partial changes committed: {type(exc).__name__}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
