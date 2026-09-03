"""Single source of truth for Bethel master-account selection.

Public reporting is controlled explicitly from Super Admin. A public master must
be deliberately selected and enabled before it can be exposed by public-facing
features. Master accounts never become public merely because one posts a newer
snapshot.

Internal analytics may still use BETHEL_MASTER_ACCOUNT as a bootstrap fallback
when no explicit public selection exists, but runtime snapshot recency is never
used to switch the selected master automatically.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.orm import Session

from api.mt5_ingest.models import MasterTerminalRegistry, PublicMt5DisplaySetting


def _selected_public_master_account(db: Session) -> Optional[str]:
    """Return the explicitly selected public owner/master terminal, if valid."""
    setting = (
        db.query(PublicMt5DisplaySetting)
        .filter(PublicMt5DisplaySetting.id == 1)
        .first()
    )
    if setting is None or not setting.enabled or setting.terminal_registry_id is None:
        return None

    terminal = (
        db.query(MasterTerminalRegistry)
        .filter(
            MasterTerminalRegistry.id == setting.terminal_registry_id,
            MasterTerminalRegistry.active.is_(True),
            MasterTerminalRegistry.subscriber_id.is_(None),
        )
        .first()
    )
    if terminal is None:
        return None

    account = str(terminal.account_number or "").strip()
    return account or None


def resolve_public_master_account(db: Session) -> Optional[str]:
    """Resolve only the master explicitly approved for public reporting.

    This function intentionally has no automatic fallback. If Super Admin has
    not selected and enabled a public master, public reporting must fail closed.
    """
    return _selected_public_master_account(db)


def resolve_active_master_account(db: Session) -> Optional[str]:
    """Resolve the company master for internal analytics without auto-switching.

    Resolution order:
      1. Explicit Super Admin public-display selection.
      2. BETHEL_MASTER_ACCOUNT as an internal/bootstrap fallback.

    The former newest-snapshot fallback is deliberately removed. A different
    master posting a newer snapshot can no longer change the active account.
    """
    selected = _selected_public_master_account(db)
    if selected:
        return selected

    configured = (os.getenv("BETHEL_MASTER_ACCOUNT") or "").strip()
    return configured or None
