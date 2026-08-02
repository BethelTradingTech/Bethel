"""Permanently clear legacy plaintext broker passwords from Bethel's SQLite database."""

import sys

from sqlalchemy import text

from api.database import SessionLocal


SENSITIVE_BROKER_COLUMNS = {
    "investor_password",
    "broker_password",
    "mt5_password",
}


def main() -> int:
    phrase = "DELETE STORED BROKER PASSWORDS"
    if input(f"Type {phrase}: ").strip() != phrase:
        print("Cancelled. No records changed.")
        return 1

    db = SessionLocal()
    try:
        tables = [
            row[0]
            for row in db.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).all()
            if row[0] and not row[0].startswith("sqlite_")
        ]
        cleared = 0
        columns_cleared = []
        for table_name in tables:
            safe_table = table_name.replace('"', '""')
            columns = [
                row[1]
                for row in db.execute(
                    text(f'PRAGMA table_info("{safe_table}")')
                ).all()
            ]
            for column_name in columns:
                if column_name.casefold() not in SENSITIVE_BROKER_COLUMNS:
                    continue
                safe_column = column_name.replace('"', '""')
                result = db.execute(text(
                    f'UPDATE "{safe_table}" '
                    f'SET "{safe_column}" = NULL '
                    f'WHERE "{safe_column}" IS NOT NULL'
                ))
                cleared += max(result.rowcount or 0, 0)
                columns_cleared.append(f"{table_name}.{column_name}")

        db.commit()
        if columns_cleared:
            print(f"Cleared {cleared} stored broker password value(s).")
            print("Sanitized columns: " + ", ".join(columns_cleared))
        else:
            print("No legacy broker-password columns exist. Nothing needed removal.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Cleanup failed safely: {type(exc).__name__}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
