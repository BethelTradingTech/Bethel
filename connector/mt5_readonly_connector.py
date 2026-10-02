"""Run on Windows beside MT5. Sends telemetry only; contains no order functions."""
from datetime import datetime, timedelta, timezone
import hashlib, hmac, json, logging, os, secrets, time

import MetaTrader5 as mt5
import requests


API = os.getenv("BETHEL_API_URL", "https://bethel-api.onrender.com").rstrip("/")
SECRET = os.getenv("MT5_CONNECTOR_SECRET", "")
CONNECTOR_ID = os.getenv("MT5_CONNECTOR_ID", "owner-laptop-1")
TERMINAL_PATH = os.getenv("BETHEL_MT5_TERMINAL_PATH", "").strip()
INTERVAL = max(int(os.getenv("MT5_SNAPSHOT_INTERVAL", "60")), 30)
HISTORY_INTERVAL = max(int(os.getenv("MT5_HISTORY_INTERVAL", "900")), 300)
HISTORY_DAYS = max(int(os.getenv("MT5_HISTORY_DAYS", "3650")), 1)
HISTORY_BATCH_SIZE = 500
LOG_PATH = os.getenv("BETHEL_CONNECTOR_LOG", "")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.StreamHandler()] + ([logging.FileHandler(LOG_PATH, encoding="utf-8")] if LOG_PATH else []))
logger = logging.getLogger("bethel.mt5.connector")
session = requests.Session()
last_history_sync = 0.0
history_backfilled_for = None


def snapshot():
    if len(SECRET) < 64:
        raise RuntimeError("MT5_CONNECTOR_SECRET must contain at least 64 characters")
    initialized = mt5.initialize(path=TERMINAL_PATH) if TERMINAL_PATH else mt5.initialize()
    if not initialized:
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
        "positions": positions, "closed_deals": [], "cash_flows": [],
    }


def _history_rows(history):
    exit_entries = {mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY, mt5.DEAL_ENTRY_INOUT}
    eligible = [deal for deal in history if deal.entry in exit_entries and deal.symbol and deal.volume > 0
                and deal.type in {mt5.DEAL_TYPE_BUY, getattr(mt5, "DEAL_TYPE_SELL", 1)}]
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
            "closed_at": datetime.fromtimestamp(
                (getattr(deal, "time_msc", 0) or deal.time * 1000) / 1000,
                timezone.utc,
            ).isoformat(),
    } for deal in eligible]

    # Keep separate charges under their original MT5 tickets. They affect
    # performance, not funding, and are never counted as completed trades.
    cost_types = {getattr(mt5, name) for name in (
        "DEAL_TYPE_CHARGE", "DEAL_TYPE_COMMISSION", "DEAL_TYPE_COMMISSION_DAILY",
        "DEAL_TYPE_COMMISSION_MONTHLY", "DEAL_TYPE_COMMISSION_AGENT_DAILY",
        "DEAL_TYPE_COMMISSION_AGENT_MONTHLY", "DEAL_TYPE_INTEREST",
        "DEAL_DIVIDEND", "DEAL_DIVIDEND_FRANKED", "DEAL_TAX",
    ) if hasattr(mt5, name)}
    exit_tickets = {deal.ticket for deal in eligible}
    for deal in history:
        entry_cost = (deal.type in {mt5.DEAL_TYPE_BUY, getattr(mt5, "DEAL_TYPE_SELL", 1)}
                      and deal.ticket not in exit_tickets)
        if not entry_cost and deal.type not in cost_types:
            continue
        profit = float(deal.profit) if not entry_cost else 0.0
        commission = float(deal.commission)
        swap = float(deal.swap)
        fee = float(getattr(deal, "fee", 0.0))
        if profit + commission + swap + fee == 0:
            continue
        closed_deals.append({
            "deal_ticket": str(deal.ticket), "position_id": str(deal.position_id),
            "order_id": str(deal.order), "symbol": deal.symbol or "LEDGER",
            "deal_type": "COST", "volume": 0.0, "price": 0.0,
            "profit": profit, "commission": commission, "swap": swap, "fee": fee,
            "closed_at": datetime.fromtimestamp(
                (getattr(deal, "time_msc", 0) or deal.time * 1000) / 1000,
                timezone.utc,
            ).isoformat(),
        })

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
            "occurred_at": datetime.fromtimestamp(
                (getattr(deal, "time_msc", 0) or deal.time * 1000) / 1000,
                timezone.utc,
            ).isoformat(),
    } for deal in history if deal.type in cash_type_names]
    return closed_deals, cash_flows


def sync_all_history(account_number):
    """Backfill all available MT5 deal history in bounded, idempotent batches."""
    global last_history_sync, history_backfilled_for
    end = datetime.now(timezone.utc)
    full_backfill = history_backfilled_for != account_number
    start = end - timedelta(days=HISTORY_DAYS if full_backfill else 7)
    total_deals = total_flows = 0
    while start < end:
        stop = min(start + timedelta(days=365), end)
        history = mt5.history_deals_get(start, stop)
        if history is None:
            raise RuntimeError(f"MT5 deal history unavailable: {mt5.last_error()}")
        deals, flows = _history_rows(history)
        for offset in range(0, max(len(deals), len(flows)), HISTORY_BATCH_SIZE):
            batch_deals = deals[offset:offset + HISTORY_BATCH_SIZE]
            batch_flows = flows[offset:offset + HISTORY_BATCH_SIZE]
            send({"account_number": account_number,
                  "closed_deals": batch_deals, "cash_flows": batch_flows}, route="history")
            total_deals += len(batch_deals)
            total_flows += len(batch_flows)
        start = stop
    last_history_sync = time.time()
    history_backfilled_for = account_number
    logger.info("history synced account=%s deals=%s cash_flows=%s", account_number, total_deals, total_flows)


def snapshot_with_history():
    """Send recent transactions with the balance they explain, every cycle."""
    for _ in range(3):
        payload = snapshot()
        end = datetime.fromisoformat(payload["observed_at"])
        history = mt5.history_deals_get(end - timedelta(days=7), end)
        if history is None:
            raise RuntimeError(f"MT5 deal history unavailable: {mt5.last_error()}")
        payload["closed_deals"], payload["cash_flows"] = _history_rows(history)
        if len(payload["closed_deals"]) > 5000 or len(payload["cash_flows"]) > 5000:
            # High-volume accounts use the existing bounded history endpoint.
            # Finish all batches before publishing the corresponding balance.
            for offset in range(0, max(len(payload["closed_deals"]), len(payload["cash_flows"])), HISTORY_BATCH_SIZE):
                send({"account_number": payload["account_number"],
                      "closed_deals": payload["closed_deals"][offset:offset + HISTORY_BATCH_SIZE],
                      "cash_flows": payload["cash_flows"][offset:offset + HISTORY_BATCH_SIZE]}, route="history")
            payload["closed_deals"], payload["cash_flows"] = [], []
        account = mt5.account_info()
        if (account is not None and str(account.login) == payload["account_number"]
                and float(account.balance) == float(payload["balance"])):
            return payload
    raise RuntimeError("MT5 balance changed during history capture; retrying next cycle")


def send(payload, route="snapshot"):
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp, nonce = str(int(time.time())), secrets.token_urlsafe(24)
    signature = hmac.new(SECRET.encode(), timestamp.encode()+b"\n"+nonce.encode()+b"\n"+body, hashlib.sha256).hexdigest()
    response = session.post(API + "/connector/v1/" + route, data=body, timeout=60, headers={
        "Content-Type":"application/json", "X-Bethel-Connector-Id":CONNECTOR_ID,
        "X-Bethel-Timestamp":timestamp, "X-Bethel-Nonce":nonce, "X-Bethel-Signature":signature,
    })
    if not response.ok:
        logger.error("snapshot rejected status=%s body=%s", response.status_code, response.text[:500])
        response.raise_for_status()


if __name__ == "__main__":
    failures = 0
    while True:
        try:
            payload = snapshot()
            if time.time() - last_history_sync >= HISTORY_INTERVAL:
                sync_all_history(payload["account_number"])
            payload = snapshot_with_history()
            send(payload)
            failures = 0
            details = []
            if payload["closed_deals"]:
                details.append(f"{len(payload['closed_deals'])} closed deals")
            if payload["cash_flows"]:
                details.append(f"{len(payload['cash_flows'])} cash-flow events")
            logger.info("snapshot accepted account=%s connector=%s%s", payload["account_number"], CONNECTOR_ID, f" with {', '.join(details)}" if details else "")
        except Exception as error:
            failures += 1
            logger.error("connector error: %s", error)
        delay = INTERVAL if failures == 0 else min(300, max(15, 2 ** min(failures, 8)))
        time.sleep(delay)
