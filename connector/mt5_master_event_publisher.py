"""Read-only fast loop that publishes master position changes to Bethel."""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import time

import MetaTrader5 as mt5
import requests


API = os.getenv("BETHEL_API_URL", "https://bethel-api.onrender.com").rstrip("/")
SECRET = os.getenv("MT5_CONNECTOR_SECRET", "")
CONNECTOR_ID = os.getenv("MT5_EVENT_CONNECTOR_ID", "owner-master-events-1")
EXPECTED_MASTER = os.getenv("BETHEL_MASTER_ACCOUNT", "49617874")
SCAN_SECONDS = max(float(os.getenv("BETHEL_MASTER_SCAN_SECONDS", "1")), 0.5)
STATE_PATH = Path(os.getenv("BETHEL_MASTER_EVENT_STATE", str(Path.home() / ".bethel-master-events.json")))
LOG_PATH = os.getenv("BETHEL_MASTER_EVENT_LOG", "")
session = requests.Session()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.StreamHandler()] + ([logging.FileHandler(LOG_PATH, encoding="utf-8")] if LOG_PATH else []))
logger = logging.getLogger("bethel.mt5.master.events")


def current_positions():
    if len(SECRET) < 64:
        raise RuntimeError("MT5_CONNECTOR_SECRET must contain at least 64 characters")
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None or str(account.login) != EXPECTED_MASTER:
        raise RuntimeError("Safety stop: this terminal is not the configured master account")
    positions = mt5.positions_get()
    if positions is None:
        raise RuntimeError(f"Master positions unavailable: {mt5.last_error()}")
    return {str(p.ticket): {
        "master_ticket": str(p.ticket), "symbol": p.symbol,
        "direction": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
        "volume": float(p.volume), "price": float(p.price_open),
        "stop_loss": float(p.sl), "take_profit": float(p.tp),
    } for p in positions}


def load_state():
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data.get("positions", {}), int(data.get("sequence", 0))
    except (FileNotFoundError, ValueError):
        return None, 0


def save_state(positions, sequence):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps({"positions": positions, "sequence": sequence}, sort_keys=True), encoding="utf-8")
    temporary.replace(STATE_PATH)


def publish(event, sequence):
    event["account_number"] = EXPECTED_MASTER
    event["event_key"] = f"{event['master_ticket']}:{event['event_type']}:{sequence}"
    body = json.dumps(event, separators=(",", ":")).encode()
    timestamp, nonce = str(int(time.time())), secrets.token_urlsafe(24)
    signature = hmac.new(SECRET.encode(), timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body, hashlib.sha256).hexdigest()
    response = session.post(API + "/copyhub/v1/master/events", data=body, timeout=20, headers={
        "Content-Type": "application/json", "X-Bethel-Connector-Id": CONNECTOR_ID,
        "X-Bethel-Timestamp": timestamp, "X-Bethel-Nonce": nonce,
        "X-Bethel-Signature": signature,
    })
    response.raise_for_status()


def changes(previous, current):
    events = []
    for ticket, position in current.items():
        old = previous.get(ticket)
        if old is None:
            events.append({**position, "event_type": "OPEN"})
            continue
        if position["volume"] < old["volume"]:
            events.append({**position, "event_type": "PARTIAL_CLOSE", "volume": round(old["volume"] - position["volume"], 8)})
        if position["stop_loss"] != old["stop_loss"] or position["take_profit"] != old["take_profit"]:
            events.append({**position, "event_type": "MODIFY"})
    for ticket, old in previous.items():
        if ticket not in current:
            events.append({**old, "event_type": "CLOSE"})
    return events


def run():
    previous, sequence = load_state()
    while True:
        try:
            current = current_positions()
            if previous is None:
                # Existing trades are not copied on first installation.
                previous = current
                save_state(previous, sequence)
                logger.info("master baseline recorded; existing positions skipped")
            else:
                for event in changes(previous, current):
                    sequence += 1
                    publish(event, sequence)
                    logger.info("published %s ticket=%s", event["event_type"], event["master_ticket"])
                previous = current
                save_state(previous, sequence)
        except Exception as error:
            logger.error("master event loop error: %s", error)
        time.sleep(SCAN_SECONDS)


if __name__ == "__main__":
    run()
