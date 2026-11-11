"""Regression tests for the local API schema preflight (stdlib only)."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import local_api_migrate


class LocalMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "bethel.db"
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TABLE client_onboarding (id INTEGER PRIMARY KEY, payment_confirmed_at TIMESTAMP)"
            )
            conn.execute(
                "INSERT INTO client_onboarding (id, payment_confirmed_at) VALUES (1, '2026-10-01 10:00:00')"
            )
        self.env = patch.dict(os.environ, {"DATABASE_URL": "sqlite:///" + self.db.as_posix()})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_migration_creates_backup_and_preserves_paid_state(self):
        local_api_migrate.main()
        with sqlite3.connect(self.db) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(client_onboarding)")}
            value = conn.execute(
                "SELECT activation_fee_satisfied_at FROM client_onboarding WHERE id=1"
            ).fetchone()[0]
        self.assertIn("activation_fee_satisfied_at", columns)
        self.assertEqual(value, "2026-10-01 10:00:00")
        backups = list((self.db.parent / "database_backups").glob("*.db"))
        self.assertEqual(len(backups), 1)
        with sqlite3.connect(backups[0]) as backup:
            self.assertEqual(backup.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_migration_is_idempotent(self):
        local_api_migrate.main()
        local_api_migrate.main()
        self.assertEqual(len(list((self.db.parent / "database_backups").glob("*.db"))), 1)

    def test_missing_database_is_not_created(self):
        self.db.unlink()
        with self.assertRaises(RuntimeError):
            local_api_migrate.main()
        self.assertFalse(self.db.exists())


if __name__ == "__main__":
    unittest.main()
