from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.operations.backup import BACKUP_DIRECTORY, DATABASE, create_backup, verify_backup


def api_running() -> bool:
    connection = socket.socket()
    connection.settimeout(1)
    try:
        return connection.connect_ex(("127.0.0.1", 8000)) == 0
    finally:
        connection.close()


parser = argparse.ArgumentParser(description="Safely restore the Bethel SQLite database.")
parser.add_argument("filename", help="Backup filename from data/backups")
parser.add_argument(
    "--confirm",
    required=True,
    help="Required literal value: RESTORE-BETHEL-DATABASE",
)
args = parser.parse_args()

if args.confirm != "RESTORE-BETHEL-DATABASE":
    raise SystemExit("Confirmation phrase is incorrect")
if api_running():
    raise SystemExit("Stop the API before restoring the database")

verification = verify_backup(args.filename)
if not verification["valid"]:
    raise SystemExit(f"Backup validation failed: {verification}")

pre_restore = create_backup("PRE_RESTORE")
source = BACKUP_DIRECTORY / Path(args.filename).name
staged = DATABASE.with_suffix(".restore-staged")
shutil.copy2(source, staged)
connection = sqlite3.connect(str(staged))
try:
    result = connection.execute("PRAGMA integrity_check").fetchone()
    if not result or str(result[0]).lower() != "ok":
        raise SystemExit(f"Staged database failed integrity check: {result}")
finally:
    connection.close()
staged.replace(DATABASE)
print("DATABASE RESTORE COMPLETE")
print("Restored:", source)
print("Pre-restore recovery backup:", pre_restore["filename"])
print("SHA-256:", verification["sha256"])
