"""Idempotent, backed-up SQLite migration for the local Bethel API.

Only updates the activation fee state column in the configured SQLite database.
Never starts MetaTrader, touches trading orders, or creates a new database.
"""
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent

def resolve_database():
    url = os.getenv("DATABASE_URL", "sqlite:///./bethel_trading.db")
    if not url.startswith("sqlite:///"):
        raise RuntimeError("Local SQLite migration requires a SQLite DATABASE_URL")
    path = unquote(url[len("sqlite:///"):].split("?", 1)[0])
    if not path or path == ":memory:":
        raise RuntimeError("Refusing to migrate an in-memory or unspecified database")
    return (ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()

def main():
    path = resolve_database()
    if not path.is_file():
        raise RuntimeError(f"Refusing to create missing database: {path}")
    with sqlite3.connect(f"file:{path.as_posix()}?mode=rw", uri=True, timeout=30) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "client_onboarding" not in tables:
            raise RuntimeError("client_onboarding table missing; migration aborted")
        columns = {row[1] for row in db.execute("PRAGMA table_info(client_onboarding)")}
        if "payment_confirmed_at" not in columns:
            raise RuntimeError("payment_confirmed_at missing; migration aborted")
        if "activation_fee_satisfied_at" in columns:
            print("Activation-fee schema already present")
            return
        backup_dir = path.parent / "database_backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / (path.stem + "_before_activation_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db")
        with sqlite3.connect(str(backup_path)) as backup:
            db.backup(backup)
            if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Backup integrity check failed; no migration applied")
        print(f"Verified SQLite backup: {backup_path}")
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("ALTER TABLE client_onboarding ADD COLUMN activation_fee_satisfied_at TIMESTAMP")
            db.execute(
                "UPDATE client_onboarding SET activation_fee_satisfied_at = payment_confirmed_at "
                "WHERE activation_fee_satisfied_at IS NULL AND payment_confirmed_at IS NOT NULL"
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        verified = {row[1] for row in db.execute("PRAGMA table_info(client_onboarding)")}
        if "activation_fee_satisfied_at" not in verified:
            raise RuntimeError("Migration verification failed")
        print("Activation-fee schema migration verified")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"API startup migration FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
