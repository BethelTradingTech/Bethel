from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock

from api.database import SessionLocal
from api.operations.models import BackupRecord


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "bethel_trading.db"
BACKUP_DIRECTORY = ROOT / "data" / "backups"
BACKUP_LOCK = Lock()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sqlite_integrity(path: Path) -> tuple[bool, str]:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        detail = str(result[0]) if result else "no result"
        return detail.lower() == "ok", detail
    finally:
        connection.close()


def latest_backup_age() -> timedelta | None:
    if not BACKUP_DIRECTORY.exists():
        return None
    files = sorted(BACKUP_DIRECTORY.glob("bethel-*.db"), key=lambda p: p.stat().st_mtime)
    if not files:
        return None
    return datetime.now() - datetime.fromtimestamp(files[-1].stat().st_mtime)


def create_backup(reason: str = "MANUAL") -> dict:
    with BACKUP_LOCK:
        if not DATABASE.exists():
            raise FileNotFoundError(f"Database not found: {DATABASE}")
        BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        filename = f"bethel-{stamp}.db"
        target = BACKUP_DIRECTORY / filename
        source_connection = sqlite3.connect(str(DATABASE), timeout=30)
        destination_connection = sqlite3.connect(str(target))
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
            source_connection.close()

        valid, integrity_detail = sqlite_integrity(target)
        if not valid:
            target.unlink(missing_ok=True)
            raise RuntimeError(f"Backup integrity failed: {integrity_detail}")

        digest = sha256_file(target)
        manifest = {
            "filename": filename,
            "sha256": digest,
            "size_bytes": target.stat().st_size,
            "reason": reason,
            "integrity_status": "OK",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        target.with_suffix(".json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        db = SessionLocal()
        try:
            db.add(BackupRecord(**{
                key: manifest[key]
                for key in (
                    "filename",
                    "sha256",
                    "size_bytes",
                    "reason",
                    "integrity_status",
                )
            }))
            db.commit()
        finally:
            db.close()
        enforce_retention()
        return manifest


def verify_backup(filename: str) -> dict:
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.endswith(".db"):
        raise ValueError("Invalid backup filename")
    path = BACKUP_DIRECTORY / safe_name
    if not path.exists():
        raise FileNotFoundError("Backup not found")
    manifest_path = path.with_suffix(".json")
    if not manifest_path.exists():
        raise FileNotFoundError("Backup manifest not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_hash = sha256_file(path)
    valid, integrity_detail = sqlite_integrity(path)
    hash_matches = actual_hash == manifest.get("sha256")
    return {
        "filename": safe_name,
        "valid": bool(valid and hash_matches),
        "sqlite_integrity": integrity_detail,
        "hash_matches": hash_matches,
        "sha256": actual_hash,
        "size_bytes": path.stat().st_size,
    }


def enforce_retention() -> int:
    days = max(int(os.getenv("BACKUP_RETENTION_DAYS", "30")), 1)
    minimum = max(int(os.getenv("BACKUP_MINIMUM_COPIES", "5")), 1)
    cutoff = datetime.now() - timedelta(days=days)
    files = sorted(
        BACKUP_DIRECTORY.glob("bethel-*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    deleted = 0
    for index, path in enumerate(files):
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if index < minimum or modified >= cutoff:
            continue
        path.unlink(missing_ok=True)
        path.with_suffix(".json").unlink(missing_ok=True)
        deleted += 1
    return deleted


def ensure_scheduled_backup() -> dict:
    interval = max(int(os.getenv("BACKUP_INTERVAL_HOURS", "6")), 1)
    age = latest_backup_age()
    if age is not None and age < timedelta(hours=interval):
        return {"status": "current", "age_seconds": int(age.total_seconds())}
    return {"status": "created", "backup": create_backup("SCHEDULED")}
