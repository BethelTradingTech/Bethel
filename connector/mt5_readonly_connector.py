"""Run on Windows beside MT5. Sends telemetry only; contains no order functions."""
from datetime import datetime, timedelta, timezone
import hashlib, hmac, json, logging, os, secrets, time

import MetaTrader5 as mt5
import requests


API = os.getenv("BETHEL_API_URL", "https://bethel-api.onrender.com").rstrip("/")
SECRET = os.getenv("MT5_CONNECTOR_SECRET", "")
CONNECTOR_ID = os.getenv("MT5_CONNECTOR_ID", "owner-laptop-1")
INTERVAL = max(int(os.getenv("MT5_SNAPSHOT_INTERVAL", "60")), 30)
HISTORY_INTERVAL = max(int(os.getenv("MT5_HISTORY_INTERVAL", "900")), 300)
HISTORY_DAYS = max(int(os.getenv("MT5_HISTORY_DAYS", "3650")), 1)
MAX_CLOSED_DEALS = min(max(int(os.getenv("MT5_MAX_CLOSED_DEALS", "5000")), 100), 5000)
LOG_PATH = os.getenv("BETHEL_CONNECTOR_LOG", "")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.StreamHandler()] + ([logging.FileHandler(LOG_PATH, encoding="utf-8")] if LOG_PATH else []))
logger = logging.getLogger("bethel.mt5.connector")
session = requests.Session()
last_history_sync = 0.0


def snapshot():
    global last_history_sync
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

    closed_deals = []
    cash_flows = []
    now_timestamp = time.time()
    if now_timestamp - last_history_sync >= HISTORY_INTERVAL:
        date_to = datetime.now(timezone.utc)
        date_from = date_to - timedelta(days=HISTORY_DAYS)
        history = mt5.history_deals_get(date_from, date_to)
        if history is None:
            raise RuntimeError(f"MT5 deal history unavailable: {mt5.last_error()}")

        exit_entries = {mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY, mt5.DEAL_ENTRY_INOUT}
        eligible = [
            deal for deal in history
            if deal.entry in exit_entries and deal.symbol and deal.volume > 0
        ][-MAX_CLOSED_DEALS:]
        closed_deals = [{
            "deal_ticket": str(deal.ticket),
            "position_id": str(deal.position_id),
            "order_id": str(deal.order),
            "symbol": deal.symbol,
            "deal_type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
            "volume": deal.volume,
            "price": deal.price,
            "profit": deal.profit,
            "commission": deal.commission,
            "swap": deal.swap,
            "fee": getattr(deal, "fee", 0.0),
            "closed_at": datetime.fromtimestamp(deal.time, timezone.utc).isoformat(),
        } for deal in eligible]

        cash_type_names = {
            mt5.DEAL_TYPE_BALANCE: "BALANCE",
            mt5.DEAL_TYPE_CREDIT: "CREDIT",
            mt5.DEAL_TYPE_BONUS: "BONUS",
            mt5.DEAL_TYPE_CORRECTION: "CORRECTION",
        }
        cash_flows = [{
            "deal_ticket": str(deal.ticket),
            "event_type": cash_type_names[deal.type],
            "amount": float(deal.profit),
            "occurred_at": datetime.fromtimestamp(deal.time, timezone.utc).isoformat(),
        } for deal in history if deal.type in cash_type_names]

        last_history_sync = now_timestamp
        logger.info(
            "prepared %s closed deals and %s cash-flow events for signed sync",
            len(closed_deals),
            len(cash_flows),
        )

    return {
        "account_number": str(account.login), "server": account.server,
        "currency": account.currency, "balance": account.balance,
        "equity": account.equity, "floating_profit": account.profit,
        "observed_at": datetime.now(timezone.utc).isoformat(), "mode": mode,
        "positions": positions,
        "closed_deals": closed_deals,
        "cash_flows": cash_flows,
    }


def send(payload):
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp, nonce = str(int(time.time())), secrets.token_urlsafe(24)
    signature = hmac.new(SECRET.encode(), timestamp.encode()+b"\n"+nonce.encode()+b"\n"+body, hashlib.sha256).hexdigest()
    response = session.post(API + "/connector/v1/snapshot", data=body, timeout=60, headers={
        "Content-Type":"application/json", "X-Bethel-Connector-Id":CONNECTOR_ID,
        "X-Bethel-Timestamp":timestamp, "X-Bethel-Nonce":nonce, "X-Bethel-Signature":signature,
    })
    response.raise_for_status()


if __name__ == "__main__":
    failures = 0
    while True:
        try:
            payload = snapshot()
            send(payload)
            failures = 0
            details = []
            if payload["closed_deals"]:
                details.append(f"{len(payload['closed_deals'])} closed deals")
            if payload["cash_flows"]:
                details.append(f"{len(payload['cash_flows'])} cash-flow events")
            logger.info("snapshot accepted%s", f" with {', '.join(details)}" if details else "")
        except Exception as error:
            failures += 1
            logger.error("connector error: %s", error)
        delay = INTERVAL if failures == 0 else min(300, max(15, 2 ** min(failures, 8)))
        time.sleep(delay)
