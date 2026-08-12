"""Refresh Bethel's local sanctions dataset from the official UK Sanctions List.

This version is designed for memory-constrained Render instances. It downloads
the source to a temporary file in chunks, hashes it incrementally, streams CSV
rows instead of decoding the whole file into RAM, and retains only compact
screening fields per designation before bulk inserting into PostgreSQL.
"""

import csv
import hashlib
import os
import re
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.database import Base, SessionLocal, engine
from api.kyc.native_models import BethelScreeningDataset, BethelScreeningEntry

UK_URL = os.getenv("UK_SANCTIONS_CSV_URL", "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv")


def _log(message):
    print(message, flush=True)


def _clean(value):
    return " ".join(str(value or "").replace("\x00", "").strip().split())


def _header_key(value):
    value = _clean(value).lstrip("\ufeff").lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def _get(row, *labels):
    for label in labels:
        value = row.get(_header_key(label))
        if value:
            return value
    return ""


def _name(row):
    return " ".join(x for x in (_get(row, f"Name {i}") for i in range(1, 7)) if x)


def _parse_dob(value):
    value = _clean(value)
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def _detect_encoding(path: str) -> str:
    with open(path, "rb") as handle:
        prefix = handle.read(4)
    if prefix.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    return "utf-8-sig"


def _open_reader(path: str):
    encoding = _detect_encoding(path)
    handle = open(path, "r", encoding=encoding, errors="replace", newline="")
    header = None
    for _ in range(50):
        line = handle.readline()
        if not line:
            break
        normalized = _header_key(line)
        if "uniqueid" in normalized and ("name6" in normalized or "name1" in normalized):
            header = line
            break
    if header is None:
        handle.close()
        raise RuntimeError("UK sanctions CSV header was not found")
    delimiter = ","
    try:
        delimiter = csv.Sniffer().sniff(header, delimiters=",;\t|").delimiter
    except csv.Error:
        pass
    reader = csv.DictReader(handle, fieldnames=next(csv.reader([header], delimiter=delimiter)), delimiter=delimiter)
    normalized_headers = {_header_key(x) for x in (reader.fieldnames or []) if x}
    required = {_header_key("Unique ID"), _header_key("Name 6")}
    if not required.issubset(normalized_headers):
        handle.close()
        raise RuntimeError(f"UK sanctions CSV required fields are missing; headers={reader.fieldnames!r}")
    return handle, reader, delimiter


def refresh():
    _log(f"[1/6] Downloading official UK sanctions list: {UK_URL}")
    request = Request(UK_URL, headers={"User-Agent": "BethelTradingTechnologies-KYC/1.3", "Accept": "text/csv,*/*;q=0.8"})
    digest = hashlib.sha256()
    total = 0
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="bethel-uksl-", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
            with urlopen(request, timeout=60) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    digest.update(chunk)
                    total += len(chunk)
        if total < 1000:
            raise RuntimeError("UK sanctions download was unexpectedly small")
        sha256 = digest.hexdigest()
        _log(f"[2/6] Downloaded {total:,} bytes to temporary storage")

        handle, reader, delimiter = _open_reader(tmp_path)
        grouped = {}
        row_count = 0
        _log(f"[3/6] Streaming designations using delimiter {delimiter!r}")
        try:
            for index, raw_row in enumerate(reader, start=1):
                row_count += 1
                row = {_header_key(k): _clean(v) for k, v in raw_row.items() if k is not None}
                name = _name(row)
                if not name:
                    continue
                uid = _get(row, "Unique ID", "UK Sanctions List Ref") or f"row-{index}"
                item = grouped.get(uid)
                if item is None:
                    item = {"names": [], "nationality": "", "country": "", "dob": None}
                    grouped[uid] = item
                if name not in item["names"]:
                    item["names"].append(name)
                is_primary = _get(row, "Name type").lower() == "primary name"
                if is_primary or not item["nationality"]:
                    item["nationality"] = _get(row, "Nationality(/ies)", "Nationality")
                if is_primary or not item["country"]:
                    item["country"] = _get(row, "Address Country", "Country")
                if is_primary or item["dob"] is None:
                    item["dob"] = _parse_dob(_get(row, "D.O.B", "DOB"))
                if row_count % 50000 == 0:
                    _log(f"      streamed {row_count:,} CSV rows; {len(grouped):,} unique designations")
        finally:
            handle.close()

        if not grouped:
            raise RuntimeError("No sanctions entries were parsed from the official UK list")
        _log(f"[4/6] Parsed {row_count:,} CSV rows into {len(grouped):,} unique designations")

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            existing = db.query(BethelScreeningDataset).filter(
                BethelScreeningDataset.dataset_type == "sanctions",
                BethelScreeningDataset.sha256 == sha256,
            ).first()
            if existing:
                existing.effective_date = date.today()
                existing.active = True
                db.query(BethelScreeningDataset).filter(
                    BethelScreeningDataset.dataset_type == "sanctions",
                    BethelScreeningDataset.id != existing.id,
                ).update({"active": False})
                db.commit()
                _log(f"[6/6] Existing dataset reactivated: id={existing.id}, records={existing.record_count}")
                return

            dataset = BethelScreeningDataset(
                dataset_type="sanctions",
                source_name="UK Sanctions List",
                source_url=UK_URL,
                sha256=sha256,
                record_count=len(grouped),
                effective_date=date.today(),
                active=False,
            )
            db.add(dataset)
            db.flush()

            _log(f"[5/6] Bulk inserting {len(grouped):,} sanctions entries")
            batch = []
            inserted = 0
            for uid, item in grouped.items():
                names = item["names"]
                batch.append({
                    "dataset_id": dataset.id,
                    "dataset_type": "sanctions",
                    "entry_key": uid,
                    "primary_name": names[0],
                    "aliases": names[1:],
                    "date_of_birth": item["dob"],
                    "nationality": item["nationality"][:3].upper() or None,
                    "countries": [item["country"]] if item["country"] else [],
                    "source_reference": uid,
                })
                if len(batch) >= 1000:
                    db.bulk_insert_mappings(BethelScreeningEntry, batch)
                    inserted += len(batch)
                    batch.clear()
                    if inserted % 10000 == 0:
                        _log(f"      inserted {inserted:,}/{len(grouped):,}")
            if batch:
                db.bulk_insert_mappings(BethelScreeningEntry, batch)
                inserted += len(batch)

            db.query(BethelScreeningDataset).filter(
                BethelScreeningDataset.dataset_type == "sanctions",
                BethelScreeningDataset.id != dataset.id,
            ).update({"active": False})
            dataset.active = True
            db.commit()
            _log(f"[6/6] Activated sanctions dataset id={dataset.id}, records={inserted:,}")
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    refresh()
