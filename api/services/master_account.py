"""Single dynamic source of truth for the currently active MT5 master account.

Runtime MT5 evidence is authoritative: whichever account owns the newest signed
EquitySnapshot is treated as the active master. Environment configuration is a
bootstrap fallback only when no verified snapshot exists yet. This prevents an
old deployment variable from pinning analytics to a previous master after the
connector is moved to a new account.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.orm import Session

from api.models import EquitySnapshot


def resolve_active_master_account(db: Session) -> Optional[str]:
    """Resolve the live master dynamically from verified runtime data.

    No account number is hard-coded. A newly connected master becomes the source
    of truth as soon as its signed MT5 snapshot is the newest snapshot stored by
    Bethel. BETHEL_MASTER_ACCOUNT is retained only for cold-start/bootstrap use.
    """
    latest = (
        db.query(EquitySnapshot)
        .filter(EquitySnapshot.account_number.isnot(None))
        .order_by(EquitySnapshot.timestamp.desc(), EquitySnapshot.id.desc())
        .first()
    )
    if latest is not None:
        account = str(latest.account_number or "").strip()
        if account:
            return account

    configured = (os.getenv("BETHEL_MASTER_ACCOUNT") or "").strip()
    return configured or None
