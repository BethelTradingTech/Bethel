"""Permanently clear legacy plaintext broker passwords from Bethel's database."""

import sys

from api.database import SessionLocal
from api.models import MT5Account


def main() -> int:
    phrase = "DELETE STORED BROKER PASSWORDS"
    if input(f"Type {phrase}: ").strip() != phrase:
        print("Cancelled. No records changed.")
        return 1

    db = SessionLocal()
    try:
        rows = db.query(MT5Account).filter(
            MT5Account.investor_password.isnot(None)
        ).all()
        for account in rows:
            account.investor_password = None
        db.commit()
        print(f"Cleared stored broker passwords from {len(rows)} account record(s).")
        return 0
    except Exception:
        db.rollback()
        print("Cleanup failed; no partial changes committed.")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
