"""Run on Windows beside MT5. Sends telemetry only; contains no order functions."""
from datetime import datetime, timezone
import hashlib, hmac, json, logging, os, secrets, time

import MetaTrader5 as mt5
import requests


API = os.getenv("BETHEL_API_URL", "https://bethel-api.onrender.com").rstrip("/")
SECRET = os.getenv("MT5_CONNECTOR_SECRET", "")
CONNECTOR_ID = os.getenv("MT5_CONNECTOR_ID", "owner-laptop-1")
INTERVAL = max(int(os.getenv("MT5_SNAPSHOT_INTERVAL", "60")), 30)
LOG_PATH = os.getenv("BETHEL_CONNECTOR_LOG", "")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.StreamHandler()] + ([logging.FileHandler(LOG_PATH, encoding="utf-8")] if LOG_PATH else []))
logger = logging.getLogger("bethel.mt5.connector")
session = requests.Session()


def snapshot():
    if len(SECRET) < 64:
        raise RuntimeError("MT5_CONNECTOR_SECRET must contain at least 64 characters")
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None:
        raise RuntimeError("MT5 account is unavailable")
    mode = "DEMO" if "demo" in account.server.casefold() else "LIVE"
    open_positions = mt5.positions_get()
    if open_positions is None:
        raise RuntimeError(f"MT5 positions unavailable: {mt5.last_error()}")
    positions = [{
        "ticket": str(position.ticket),
        "symbol": position.symbol,
        "direction": "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL",
        "volume": position.volume,
        "open_price": position.price_open,
        "current_price": position.price_current,
        "stop_loss": position.sl,
        "take_profit": position.tp,
        "profit": position.profit,
        "swap": position.swap,
        "opened_at": datetime.fromtimestamp(position.time, timezone.utc).isoformat(),
    } for position in open_positions]
    return {
        "account_number": str(account.login), "server": account.server,
        "currency": account.currency, "balance": account.balance,
        "equity": account.equity, "floating_profit": account.profit,
        "observed_at": datetime.now(timezone.utc).isoformat(), "mode": mode,
        "positions": positions,
    }


def send(payload):
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp, nonce = str(int(time.time())), secrets.token_urlsafe(24)
    signature = hmac.new(SECRET.encode(), timestamp.encode()+b"\n"+nonce.encode()+b"\n"+body, hashlib.sha256).hexdigest()
    response = session.post(API + "/connector/v1/snapshot", data=body, timeout=20, headers={
        "Content-Type":"application/json", "X-Bethel-Connector-Id":CONNECTOR_ID,
        "X-Bethel-Timestamp":timestamp, "X-Bethel-Nonce":nonce, "X-Bethel-Signature":signature,
    })
    response.raise_for_status()


if __name__ == "__main__":
    failures = 0
    while True:
        try:
            send(snapshot()); failures = 0; logger.info("snapshot accepted")
        except Exception as error:
            failures += 1; logger.error("connector error: %s", error)
        delay = INTERVAL if failures == 0 else min(300, max(15, 2 ** min(failures, 8)))
        time.sleep(delay)
