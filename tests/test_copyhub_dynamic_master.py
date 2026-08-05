from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.copyhub.models import CopyChannel
from api.copyhub.routes import get_or_create_channel
from api.models import EquitySnapshot


def _snapshot(account_number: str, timestamp: datetime):
    return EquitySnapshot(
        account_number=account_number,
        balance=10000.0,
        equity=10000.0,
        timestamp=timestamp,
    )


def test_copyhub_follows_latest_master_without_recreating_channel_or_resetting_pause():
    engine = create_engine("sqlite:///:memory:")
    EquitySnapshot.__table__.create(engine)
    CopyChannel.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    start = datetime(2026, 8, 1, 9, 0)
    db.add(_snapshot("11111111", start))
    db.commit()

    channel = get_or_create_channel(db)
    original_id = channel.id
    channel.globally_paused = False
    db.commit()

    db.add(_snapshot("22222222", start + timedelta(days=1)))
    db.commit()

    refreshed = get_or_create_channel(db)
    db.commit()

    assert refreshed.id == original_id
    assert refreshed.master_account == "22222222"
    assert refreshed.globally_paused is False
    assert db.query(CopyChannel).count() == 1


def test_copyhub_source_contains_no_specific_master_account_constant():
    source = Path("api/copyhub/routes.py").read_text(encoding="utf-8")
    assert "MASTER_ACCOUNT" not in source
    assert "49617874" not in source
