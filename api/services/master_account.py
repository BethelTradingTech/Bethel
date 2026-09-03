"""Single source of truth for Bethel master-account selection.

Public reporting is controlled explicitly from Super Admin by the selected
owner/master terminal. Live telemetry visibility is a separate setting: a master
can remain the source for monthly/yearly public reports while live MT5 telemetry
stays disabled. Master accounts never become public merely because one posts a
newer snapshot.

Internal analytics may still use BETHEL_MASTER_ACCOUNT as a bootstrap fallback
when no explicit master selection exists, but runtime snapshot recency is never
used to switch the selected master automatically.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.orm import Session

from api.mt5_ingest.models import MasterTerminalRegistry, PublicMt5DisplaySetting


def _selected_public_master_account(db: Session) -> Optional[str]:
    """Return the explicitly selected owner/master terminal, if valid.

    The selected terminal remains authoritative for public monthly/yearly reports
    even when live MT5 telemetry is disabled. The ``enabled`` flag on
    PublicMt5DisplaySetting controls live telemetry publication only.
    """
    setting = (
        db.query(PublicMt5DisplaySetting)
        .filter(PublicMt5DisplaySetting.id == 1)
        .first()
    )
    if setting is None or setting.terminal_registry_id is None:
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
    """Resolve only the master explicitly selected for public reporting.

    This function intentionally has no automatic fallback. If Super Admin has
    not selected an eligible owner/master terminal, public reporting fails closed.
    """
    return _selected_public_master_account(db)


def resolve_active_master_account(db: Session) -> Optional[str]:
    """Resolve the company master for internal analytics without auto-switching.

    Resolution order:
      1. Explicit Super Admin owner/master selection.
      2. BETHEL_MASTER_ACCOUNT as an internal/bootstrap fallback.

    Runtime snapshot recency is deliberately never used to choose an account.
    """
    selected = _selected_public_master_account(db)
    if selected:
        return selected

    configured = (os.getenv("BETHEL_MASTER_ACCOUNT") or "").strip()
    return configured or None
