"""Single dynamic source of truth for the currently active MT5 master account.

Runtime MT5 evidence is authoritative. The newest signed EquitySnapshot belonging
to an active owner/master terminal is treated as the active master. Environment
configuration is a cold-start fallback only. Subscriber-assigned terminals are
never allowed to take over the company master merely because they posted a newer
snapshot.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.orm import Session

from api.models import EquitySnapshot
from api.mt5_ingest.models import MasterTerminalRegistry


def resolve_active_master_account(db: Session) -> Optional[str]:
    """Resolve the active company master from verified runtime data.

    No account number is hard-coded. Once a different active owner/master terminal
    starts publishing signed snapshots, that account automatically becomes the
    source for analytics, history and public performance. BETHEL_MASTER_ACCOUNT is
    retained only for cold-start/bootstrap use when no runtime evidence exists.
    """
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
