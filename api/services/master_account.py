"""Single dynamic source of truth for the selected MT5 master account.

The public master selected in Super Admin is authoritative while that public
selection is enabled. No account number is hard-coded. The selected terminal
continues to drive analytics, history and public performance until an admin
changes the selection. Runtime snapshot discovery remains a fallback for
cold-start/legacy operation when no valid public selection exists.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.orm import Session

from api.models import EquitySnapshot
from api.mt5_ingest.models import MasterTerminalRegistry, PublicMt5DisplaySetting


def _selected_public_master_account(db: Session) -> Optional[str]:
    """Return the explicitly selected public owner/master terminal, if valid.

    The selection is persistent database state. It does not change simply because
    another master posts a newer snapshot. This is what keeps the website,
    monthly returns and yearly returns attached to the account selected by Admin
    until Admin deliberately selects a different terminal.
    """
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


def resolve_active_master_account(db: Session) -> Optional[str]:
    """Resolve the selected company master without hard-coding any account.

    Resolution order:
      1. Explicit Super Admin public-display selection.
      2. Newest signed snapshot from an active owner/master terminal.
      3. BETHEL_MASTER_ACCOUNT only as a cold-start/bootstrap fallback.

    Therefore, once Admin selects a master for public display, that same account
    remains the source for its balance/equity, monthly returns, yearly returns and
    performance history until Admin changes the selection.
    """
    selected = _selected_public_master_account(db)
    if selected:
        return selected

    owner_accounts = [
        str(row[0]).strip()
        for row in db.query(MasterTerminalRegistry.account_number).filter(
            MasterTerminalRegistry.active.is_(True),
            MasterTerminalRegistry.subscriber_id.is_(None),
            MasterTerminalRegistry.account_number.isnot(None),
        ).all()
        if str(row[0] or "").strip()
    ]

    query = db.query(EquitySnapshot).filter(EquitySnapshot.account_number.isnot(None))
    if owner_accounts:
        query = query.filter(EquitySnapshot.account_number.in_(owner_accounts))

    latest = query.order_by(
        EquitySnapshot.timestamp.desc(),
        EquitySnapshot.id.desc(),
    ).first()
    if latest is not None:
        account = str(latest.account_number or "").strip()
        if account:
            return account

    configured = (os.getenv("BETHEL_MASTER_ACCOUNT") or "").strip()
    return configured or None
