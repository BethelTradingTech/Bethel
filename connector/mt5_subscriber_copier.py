"""Bethel subscriber copier for Windows MT5 terminals.

This process must run beside a *subscriber* MT5 installation. It refuses the
master account and fails closed unless every account and environment gate
matches its authorization.
"""
from decimal import Decimal, ROUND_DOWN
import json
import logging
import os
from pathlib import Path
import time

import MetaTrader5 as mt5
import requests


API = os.getenv("BETHEL_API_URL", "https://bethel-api.onrender.com").rstrip("/")
TOKEN = os.getenv("BETHEL_RECEIVER_TOKEN", "")
EXPECTED_ACCOUNT = os.getenv("BETHEL_SUBSCRIBER_ACCOUNT", "")
EXPECTED_MODE = os.getenv("BETHEL_SUBSCRIBER_MODE", "DEMO").upper()
TERMINAL_PATH = os.getenv("BETHEL_SUBSCRIBER_TERMINAL_PATH", "")
ALLOW_LIVE = os.getenv("BETHEL_ALLOW_LIVE", "false").lower() == "true"
POLL_SECONDS = max(float(os.getenv("BETHEL_COPY_POLL_SECONDS", "1")), 0.5)
DEVIATION = max(int(os.getenv("BETHEL_COPY_DEVIATION", "20")), 0)
MAGIC = int(os.getenv("BETHEL_COPY_MAGIC", "49617874"))
STATE_PATH = Path(os.getenv("BETHEL_COPIER_STATE", str(Path.home() / ".bethel-copier-state.json")))
LOG_PATH = os.getenv("BETHEL_COPIER_LOG", "")
MASTER_ACCOUNT = "49617874"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.StreamHandler()] + ([logging.FileHandler(LOG_PATH, encoding="utf-8")] if LOG_PATH else []))
logger = logging.getLogger("bethel.mt5.subscriber")
session = requests.Session()


def initialize_terminal():
    if len(TOKEN) < 48 or not EXPECTED_ACCOUNT:
        raise RuntimeError("Receiver token and subscriber account are required")
    if EXPECTED_ACCOUNT == MASTER_ACCOUNT:
        raise RuntimeError("Safety stop: the master account can never run the subscriber copier")
    initialized = mt5.initialize(path=TERMINAL_PATH) if TERMINAL_PATH else mt5.initialize()
    if not initialized:
        raise RuntimeError(f"Subscriber MT5 initialization failed: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None or str(account.login) != EXPECTED_ACCOUNT:
        raise RuntimeError("Safety stop: connected MT5 login is not the authorized subscriber")
    mode = "DEMO" if "demo" in str(account.server).casefold() else "LIVE"
    if mode != EXPECTED_MODE:
        raise RuntimeError("Safety stop: terminal DEMO/LIVE mode mismatch")
    if mode == "LIVE" and not ALLOW_LIVE:
        raise RuntimeError("Safety stop: live copying is disabled on this computer")
    if not account.trade_allowed:
        raise RuntimeError("MT5 trading is not allowed; enable Algo Trading in the subscriber terminal")
    return account, mode


def symbol_metadata(symbol):
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Symbol {symbol} is unavailable")
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"Symbol metadata unavailable for {symbol}")
    return info


def volume_for(info, requested):
    step = Decimal(str(info.volume_step))
    value = (Decimal(str(requested)) / step).quantize(Decimal("1"), rounding=ROUND_DOWN) * step
    value = max(Decimal(str(info.volume_min)), min(value, Decimal(str(info.volume_max))))
    return float(value)


def load_state():
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        state.setdefault("tickets", {})
        state.setdefault("completed", {})
        return state
    except (FileNotFoundError, ValueError):
        return {"tickets": {}, "completed": {}}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
    temporary.replace(STATE_PATH)


def find_position(ticket):
    positions = mt5.positions_get(ticket=int(ticket))
    return positions[0] if positions else None


def market_request(event, *, close_position=None, close_volume=None):
    info = symbol_metadata(event["symbol"])
    tick = mt5.symbol_info_tick(event["symbol"])
    if tick is None:
        raise RuntimeError("Current market price is unavailable")
    opening = close_position is None
    direction = event["direction"] if opening else ("SELL" if close_position.type == mt5.POSITION_TYPE_BUY else "BUY")
    volume = volume_for(info, event["volume"] if opening else close_volume)
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": event["symbol"], "volume": volume,
        "type": order_type, "price": tick.ask if direction == "BUY" else tick.bid,
        "deviation": DEVIATION, "magic": MAGIC,
        "comment": f"Bethel {event['master_ticket']}"[:31],
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": info.filling_mode,
    }
    if opening:
        request["sl"] = event.get("stop_loss") or 0.0
        request["tp"] = event.get("take_profit") or 0.0
    else:
        request["position"] = close_position.ticket
    return request


def send_checked(request):
    check = mt5.order_check(request)
    if check is None or check.retcode != 0:
        raise RuntimeError(f"MT5 order check failed: {check or mt5.last_error()}")
    result = mt5.order_send(request)
    accepted = {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL, mt5.TRADE_RETCODE_PLACED}
    if result is None or result.retcode not in accepted:
        raise RuntimeError(f"MT5 rejected copy operation: {result or mt5.last_error()}")
    return result


def execute(event, state):
    completed = state["completed"].get(event["event_key"])
    if completed:
        return completed["ticket"], completed["message"]
    master_ticket = event["master_ticket"]
    mapped = state["tickets"].get(master_ticket)
    if event["event_type"] == "OPEN":
        if mapped and find_position(mapped):
            ticket, message = mapped, "already open"
            remember_completed(event, state, ticket, message)
            return ticket, message
        result = send_checked(market_request(event))
        subscriber_ticket = str(result.order or result.deal)
        state["tickets"][master_ticket] = subscriber_ticket
        message = "opened"
        remember_completed(event, state, subscriber_ticket, message)
        return subscriber_ticket, message
    if not mapped:
        raise RuntimeError("No subscriber position mapping exists for the master ticket")
    position = find_position(mapped)
    if position is None:
        if event["event_type"] == "CLOSE":
            state["tickets"].pop(master_ticket, None)
            remember_completed(event, state, mapped, "already closed")
            return mapped, "already closed"
        raise RuntimeError("Mapped subscriber position is unavailable")
    if event["event_type"] == "MODIFY":
        result = send_checked({"action": mt5.TRADE_ACTION_SLTP, "position": position.ticket, "symbol": position.symbol, "sl": event.get("stop_loss") or 0.0, "tp": event.get("take_profit") or 0.0, "magic": MAGIC})
        ticket, message = str(position.ticket), f"modified {result.retcode}"
        remember_completed(event, state, ticket, message)
        return ticket, message
    close_volume = position.volume if event["event_type"] == "CLOSE" else min(position.volume, event["volume"])
    result = send_checked(market_request(event, close_position=position, close_volume=close_volume))
    if event["event_type"] == "CLOSE" or close_volume >= position.volume:
        state["tickets"].pop(master_ticket, None)
    ticket, message = str(position.ticket), f"closed {result.retcode}"
    remember_completed(event, state, ticket, message)
    return ticket, message


def remember_completed(event, state, ticket, message):
    state["completed"][event["event_key"]] = {"ticket": ticket, "message": message}
    while len(state["completed"]) > 5000:
        state["completed"].pop(next(iter(state["completed"])))
    save_state(state)


def api(method, path, **kwargs):
    response = session.request(method, API + path, timeout=20, headers={"Authorization": f"Bearer {TOKEN}"}, **kwargs)
    response.raise_for_status()
    return response.json()


def heartbeat(account, mode):
    info = symbol_metadata("EURUSD")
    currency = str(account.currency).upper()
    unit = "USC" if currency in {"USC", "USCENT", "USCENTS", "CENT"} else "USD"
    return api("POST", "/copyhub/v1/receiver/heartbeat", json={
        "account_number": str(account.login), "environment": mode,
        "currency_unit": unit, "is_cent_account": unit == "USC",
        "contract_size": info.trade_contract_size, "min_lot": info.volume_min,
        "max_lot": info.volume_max, "lot_step": info.volume_step,
    })


def run():
    account, mode = initialize_terminal()
    state, last_heartbeat = load_state(), 0.0
    logger.info("subscriber copier ready account=%s mode=%s", account.login, mode)
    while True:
        try:
            if time.time() - last_heartbeat >= 30:
                heartbeat(account, mode); last_heartbeat = time.time()
            response = api("GET", "/copyhub/v1/receiver/events?limit=50")
            for event in response.get("events", []):
                try:
                    ticket, message = execute(event, state)
                    api("POST", f"/copyhub/v1/receiver/deliveries/{event['delivery_id']}/ack", json={"status": "ACKNOWLEDGED", "receiver_ticket": ticket, "message": message})
                    logger.info("copied %s %s", event["event_type"], event["event_key"])
                except Exception as error:
                    api("POST", f"/copyhub/v1/receiver/deliveries/{event['delivery_id']}/ack", json={"status": "FAILED", "message": str(error)[:500]})
                    logger.error("copy failed %s: %s", event["event_key"], error)
        except Exception as error:
            logger.error("copier loop error: %s", error)
            time.sleep(min(15, POLL_SECONDS * 5))
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()
