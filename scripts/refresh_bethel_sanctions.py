"""Refresh Bethel's local sanctions dataset from the official UK Sanctions List.

Designed for a Render Cron Job. It downloads only public sanctions data; no
subscriber data leaves Bethel. The previous active snapshot is retained if a
refresh fails, and a new snapshot is activated only after records are parsed.
"""

import csv
import hashlib
import io
import os
import sys
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.database import Base, SessionLocal, engine
from api.kyc.native_models import BethelScreeningDataset, BethelScreeningEntry

UK_URL = os.getenv("UK_SANCTIONS_CSV_URL", "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv")


def _clean(value):
    return " ".join(str(value or "").strip().split())


def _name(row):
    parts = [_clean(row.get(f"Name {i}")) for i in range(1, 7)]
    return " ".join(x for x in parts if x)


def refresh():
    request = Request(UK_URL, headers={"User-Agent": "BethelTradingTechnologies-KYC/1.0"})
    with urlopen(request, timeout=60) as response:
        raw = response.read()
    if len(raw) < 1000:
        raise RuntimeError("UK sanctions download was unexpectedly small")
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    grouped = {}
    for index, row in enumerate(reader, start=1):
        name = _name(row)
        if not name:
            continue
        uid = _clean(row.get("Unique ID")) or _clean(row.get("UK Sanctions List Ref")) or f"row-{index}"
        item = grouped.setdefault(uid, {"names": [], "row": row})
        if name not in item["names"]:
            item["names"].append(name)
    if not grouped:
        raise RuntimeError("No sanctions entries were parsed from the official UK list")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(BethelScreeningDataset).filter(BethelScreeningDataset.dataset_type == "sanctions", BethelScreeningDataset.sha256 == digest).first()
        if existing:
            existing.effective_date = date.today()
            existing.active = True
            db.query(BethelScreeningDataset).filter(BethelScreeningDataset.dataset_type == "sanctions", BethelScreeningDataset.id != existing.id).update({"active": False})
            db.commit()
            print({"status": "ok", "dataset_id": existing.id, "records": existing.record_count, "unchanged": True, "sha256": digest})
            return

        dataset = BethelScreeningDataset(dataset_type="sanctions", source_name="UK Sanctions List", source_url=UK_URL, sha256=digest, record_count=len(grouped), effective_date=date.today(), active=False)
        db.add(dataset)
        db.flush()
        for uid, item in grouped.items():
            names = item["names"]
            row = item["row"]
            db.add(BethelScreeningEntry(dataset_id=dataset.id, dataset_type="sanctions", entry_key=uid, primary_name=names[0], aliases=names[1:], nationality=_clean(row.get("Nationality"))[:3].upper() or None, countries=[_clean(row.get("Country"))] if _clean(row.get("Country")) else [], source_reference=uid))
        db.flush()
        db.query(BethelScreeningDataset).filter(BethelScreeningDataset.dataset_type == "sanctions", BethelScreeningDataset.id != dataset.id).update({"active": False})
        dataset.active = True
        db.commit()
        print({"status": "ok", "dataset_id": dataset.id, "records": len(grouped), "source": dataset.source_name, "sha256": digest})
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    refresh()
