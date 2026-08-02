"""Run on Windows beside MT5. Sends telemetry only; contains no order functions."""
from datetime import datetime, timezone
import hashlib, hmac, json, os, secrets, time

import MetaTrader5 as mt5
import requests


API = os.getenv("BETHEL_API_URL", "https://bethel-api.onrender.com").rstrip("/")
SECRET = os.getenv("MT5_CONNECTOR_SECRET", "")
CONNECTOR_ID = os.getenv("MT5_CONNECTOR_ID", "owner-laptop-1")
INTERVAL = max(int(os.getenv("MT5_SNAPSHOT_INTERVAL", "60")), 30)


def snapshot():
    if len(SECRET) < 64:
        raise RuntimeError("MT5_CONNECTOR_SECRET must contain at least 64 characters")
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None:
        raise RuntimeError("MT5 account is unavailable")
    mode = "DEMO" if "demo" in account.server.casefold() else "LIVE"
    return {
        "account_number": str(account.login), "server": account.server,
        "currency": account.currency, "balance": account.balance,
        "equity": account.equity, "floating_profit": account.profit,
        "observed_at": datetime.now(timezone.utc).isoformat(), "mode": mode,
    }


def send(payload):
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp, nonce = str(int(time.time())), secrets.token_urlsafe(24)
    signature = hmac.new(SECRET.encode(), timestamp.encode()+b"\n"+nonce.encode()+b"\n"+body, hashlib.sha256).hexdigest()
    response = requests.post(API + "/connector/v1/snapshot", data=body, timeout=20, headers={
        "Content-Type":"application/json", "X-Bethel-Connector-Id":CONNECTOR_ID,
        "X-Bethel-Timestamp":timestamp, "X-Bethel-Nonce":nonce, "X-Bethel-Signature":signature,
    })
    response.raise_for_status()


if __name__ == "__main__":
    while True:
        try:
            send(snapshot()); print(datetime.now().isoformat(), "snapshot accepted")
        except Exception as error:
            print(datetime.now().isoformat(), "connector error:", error)
        time.sleep(INTERVAL)
