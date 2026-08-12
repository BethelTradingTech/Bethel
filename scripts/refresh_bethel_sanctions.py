"""Refresh Bethel's local sanctions dataset from the official UK Sanctions List.

Designed for a Render Cron Job. It downloads only public sanctions data; no
subscriber data leaves Bethel. The previous active snapshot is retained if a
refresh fails, and a new snapshot is activated only after records are parsed.

The FCDO CSV has a static URL, but this parser deliberately tolerates BOMs,
UTF-16/UTF-8 encodings, delimiter changes, a leading preamble, and harmless
header-spacing/case changes. It still fails closed if the required UKSL fields
cannot be identified or if zero designations are parsed.
"""

import csv
import hashlib
import io
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.database import Base, SessionLocal, engine
from api.kyc.native_models import BethelScreeningDataset, BethelScreeningEntry

UK_URL = os.getenv("UK_SANCTIONS_CSV_URL", "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv")


def _clean(value):
    return " ".join(str(value or "").replace("\x00", "").strip().split())


def _header_key(value):
    value = _clean(value).lstrip("\ufeff").lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def _decode(raw: bytes) -> str:
    # The published file has changed encoding historically. Prefer BOM-aware
    # decoding and fall back conservatively instead of silently producing rows
    # whose header names contain NUL characters.
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            return raw.decode("cp1252")


def _delimiter_and_header(text: str):
    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines[:50]):
        normalized = _header_key(line)
        if "uniqueid" in normalized and ("name6" in normalized or "name1" in normalized):
            header_index = index
            break
    if header_index is None:
        # Some CSV writers quote or otherwise decorate the line in ways that
        # make the compact check too strict. Look for the two required labels.
        for index, line in enumerate(lines[:50]):
            lowered = line.lower()
            if "unique id" in lowered and "name 6" in lowered:
                header_index = index
                break
    if header_index is None:
        preview = " | ".join(_clean(x)[:180] for x in lines[:3])
        raise RuntimeError(f"UK sanctions CSV header was not found; preview={preview!r}")

    body = "\n".join(lines[header_index:])
    sample = body[:16384]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    return delimiter, body


def _canonical_row(row):
    return {_header_key(key): _clean(value) for key, value in row.items() if key is not None}


def _get(row, *labels):
    for label in labels:
        value = row.get(_header_key(label))
        if value:
            return value
    return ""


def _name(row):
    parts = [_get(row, f"Name {i}") for i in range(1, 7)]
    return " ".join(x for x in parts if x)


def _parse_dob(value):
    value = _clean(value)
    if not value:
        return None
    # UKSL permits partial DOBs. Persist only an unambiguous complete date;
    # partial dates must not be converted into invented values.
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def refresh():
    request = Request(UK_URL, headers={"User-Agent": "BethelTradingTechnologies-KYC/1.1", "Accept": "text/csv,*/*;q=0.8"})
    with urlopen(request, timeout=60) as response:
        raw = response.read()
    if len(raw) < 1000:
        raise RuntimeError("UK sanctions download was unexpectedly small")

    digest = hashlib.sha256(raw).hexdigest()
    text = _decode(raw)
    delimiter, csv_body = _delimiter_and_header(text)
    reader = csv.DictReader(io.StringIO(csv_body), delimiter=delimiter)
    if not reader.fieldnames:
        raise RuntimeError("UK sanctions CSV has no field names")

    normalized_headers = {_header_key(x) for x in reader.fieldnames if x}
    required = {_header_key("Unique ID"), _header_key("Name 6")}
    if not required.issubset(normalized_headers):
        raise RuntimeError(f"UK sanctions CSV required fields are missing; headers={reader.fieldnames!r}")

    grouped = {}
    for index, raw_row in enumerate(reader, start=1):
        row = _canonical_row(raw_row)
        name = _name(row)
        if not name:
            continue
        uid = _get(row, "Unique ID", "UK Sanctions List Ref") or f"row-{index}"
        item = grouped.setdefault(uid, {"names": [], "row": row})
        if name not in item["names"]:
            item["names"].append(name)
        # Prefer the primary-name row as the metadata source when present.
        if _get(row, "Name type").lower() == "primary name":
            item["row"] = row

    if not grouped:
        raise RuntimeError("No sanctions entries were parsed from the official UK list")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(BethelScreeningDataset).filter(
            BethelScreeningDataset.dataset_type == "sanctions",
            BethelScreeningDataset.sha256 == digest,
        ).first()
        if existing:
            existing.effective_date = date.today()
            existing.active = True
            db.query(BethelScreeningDataset).filter(
                BethelScreeningDataset.dataset_type == "sanctions",
                BethelScreeningDataset.id != existing.id,
            ).update({"active": False})
            db.commit()
            print({"status": "ok", "dataset_id": existing.id, "records": existing.record_count, "unchanged": True, "sha256": digest})
            return

        dataset = BethelScreeningDataset(
            dataset_type="sanctions",
            source_name="UK Sanctions List",
            source_url=UK_URL,
            sha256=digest,
            record_count=len(grouped),
            effective_date=date.today(),
            active=False,
        )
        db.add(dataset)
        db.flush()

        for uid, item in grouped.items():
            names = item["names"]
            row = item["row"]
            nationality = _get(row, "Nationality(/ies)", "Nationality")
            address_country = _get(row, "Address Country", "Country")
            db.add(
                BethelScreeningEntry(
                    dataset_id=dataset.id,
                    dataset_type="sanctions",
                    entry_key=uid,
                    primary_name=names[0],
                    aliases=names[1:],
                    date_of_birth=_parse_dob(_get(row, "D.O.B", "DOB")),
                    nationality=nationality[:3].upper() or None,
                    countries=[address_country] if address_country else [],
                    source_reference=uid,
                )
            )

        db.flush()
        db.query(BethelScreeningDataset).filter(
            BethelScreeningDataset.dataset_type == "sanctions",
            BethelScreeningDataset.id != dataset.id,
        ).update({"active": False})
        dataset.active = True
        db.commit()
        print({"status": "ok", "dataset_id": dataset.id, "records": len(grouped), "source": dataset.source_name, "sha256": digest, "delimiter": delimiter})
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    refresh()
