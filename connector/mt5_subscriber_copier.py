"""Bethel package-routed subscriber copier for Windows MT5 terminals.

The Bethel API never places orders itself. This process runs locally beside the
subscriber's explicitly selected MT5 terminal and executes only server-signed,
package-authorized delivery events. It fails closed on account mismatch,
stale OPEN events, repeated execution errors, disabled server execution, or
LIVE-mode authorization mismatch.
"""
from datetime import datetime, timezone
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
EXPECTED_ACCOUNT = os.getenv("BETHEL_SUBSCRIBER_ACCOUNT", "").strip()
EXPECTED_MODE = os.getenv("BETHEL_SUBSCRIBER_MODE", "DEMO").upper()
TERMINAL_PATH = os.getenv("BETHEL_SUBSCRIBER_TERMINAL_PATH", "").strip()
ALLOW_LIVE = os.getenv("BETHEL_ALLOW_LIVE", "false").lower() == "true"
POLL_SECONDS = max(float(os.getenv("BETHEL_COPY_POLL_SECONDS", "1")), 0.5)
DEVIATION = max(int(os.getenv("BETHEL_COPY_DEVIATION", "20")), 0)
MAGIC = int(os.getenv("BETHEL_COPY_MAGIC", "49617874"))
MAX_STALE_OPEN_SECONDS = max(int(os.getenv("BETHEL_MAX_STALE_OPEN_SECONDS", "120")), 30)
FAILURE_CIRCUIT_THRESHOLD = max(int(os.getenv("BETHEL_COPY_FAILURE_THRESHOLD", "3")), 2)
FAILURE_CIRCUIT_SECONDS = max(int(os.getenv("BETHEL_COPY_FAILURE_COOLDOWN", "60")), 15)
STATE_PATH = Path(os.getenv("BETHEL_COPIER_STATE", str(Path.home() / f".bethel-copier-state-{EXPECTED_ACCOUNT or 'unconfigured'}.json")))
LOG_PATH = os.getenv("BETHEL_COPIER_LOG", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.StreamHandler()] + ([logging.FileHandler(LOG_PATH, encoding="utf-8")] if LOG_PATH else []))
logger = logging.getLogger("bethel.mt5.subscriber")
session = requests.Session()


class LocalHealthReasoner:
    """Auditable fail-closed local reasoning; never changes trade strategy."""

    def __init__(self):
        self.execution_failures = 0
        self.circuit_until = 0.0

    def execution_ok(self):
        self.execution_failures = 0
        self.circuit_until = 0.0

    def execution_failed(self):
        self.execution_failures += 1
        if self.execution_failures >= FAILURE_CIRCUIT_THRESHOLD:
            self.circuit_until = max(self.circuit_until, time.time() + FAILURE_CIRCUIT_SECONDS)

    def can_execute(self):
        return time.time() >= self.circuit_until

    def status(self):
        return {
            "execution_failures": self.execution_failures,
            "circuit_open": not self.can_execute(),
            "circuit_seconds_remaining": max(0, int(self.circuit_until - time.time())),
        }


health = LocalHealthReasoner()


def initialize_terminal():
    if len(TOKEN) < 48 or not EXPECTED_ACCOUNT:
        raise RuntimeError("Receiver token and subscriber account are required")
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


def revalidate_terminal():
    account = mt5.account_info()
    if account is None or str(account.login) != EXPECTED_ACCOUNT:
        raise RuntimeError("Safety stop: MT5 account changed while copier was running")
    mode = "DEMO" if "demo" in str(account.server).casefold() else "LIVE"
    if mode != EXPECTED_MODE or (mode == "LIVE" and not ALLOW_LIVE):
        raise RuntimeError("Safety stop: MT5 environment changed while copier was running")
    if not account.trade_allowed:
        raise RuntimeError("Safety stop: Algo Trading is no longer allowed")
    return account, mode


def symbol_metadata(symbol):
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Symbol {symbol} is unavailable")
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"Symbol metadata unavailable for {symbol}")
    return info


def volume_for(info, requested):
    requested_value = Decimal(str(requested))
    minimum = Decimal(str(info.volume_min))
    maximum = Decimal(str(info.volume_max))
    step = Decimal(str(info.volume_step))
    if requested_value < minimum:
        raise RuntimeError(
            f"Requested copy volume {requested} is below broker minimum {info.volume_min}; refusing to oversize"
        )
    value = (requested_value / step).quantize(Decimal("1"), rounding=ROUND_DOWN) * step
    value = min(value, maximum)
    if value < minimum or value <= 0:
        raise RuntimeError("Calculated copy volume is not tradable")
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
    try:
        positions = mt5.positions_get(ticket=int(ticket))
    except (TypeError, ValueError):
        positions = None
    return positions[0] if positions else None


def find_position_by_master_ticket(master_ticket):
    prefix = f"Bethel {master_ticket}"[:31]
    positions = mt5.positions_get() or []
    candidates = [
        p for p in positions
        if int(getattr(p, "magic", 0) or 0) == MAGIC
        and str(getattr(p, "comment", "")) == prefix
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: int(getattr(p, "time_msc", 0) or 0))


def recover_state_from_terminal(state):
    recovered = 0
    positions = mt5.positions_get() or []
    for position in positions:
        if int(getattr(position, "magic", 0) or 0) != MAGIC:
            continue
        comment = str(getattr(position, "comment", ""))
        if not comment.startswith("Bethel "):
            continue
        master_ticket = comment[len("Bethel "):].strip()
        if master_ticket and state["tickets"].get(master_ticket) != str(position.ticket):
            state["tickets"][master_ticket] = str(position.ticket)
            recovered += 1
    if recovered:
        save_state(state)
        logger.info("recovered %s Bethel position mappings from MT5", recovered)


def market_request(event, *, close_position=None, close_volume=None):
    info = symbol_metadata(event["symbol"])
    tick = mt5.symbol_info_tick(event["symbol"])
    if tick is None:
        raise RuntimeError("Current market price is unavailable")
    opening = close_position is None
    direction = event["direction"] if opening else ("SELL" if close_position.type == mt5.POSITION_TYPE_BUY else "BUY")
    requested_volume = event["volume"] if opening else close_volume
    volume = volume_for(info, requested_volume)
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": event["symbol"],
        "volume": volume,
        "type": order_type,
        "price": tick.ask if direction == "BUY" else tick.bid,
        "deviation": DEVIATION,
        "magic": MAGIC,
        "comment": f"Bethel {event['master_ticket']}"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": info.filling_mode,
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


def remember_completed(event, state, ticket, message):
    state["completed"][event["event_key"]] = {"ticket": ticket, "message": message}
    while len(state["completed"]) > 5000:
        state["completed"].pop(next(iter(state["completed"])))
    save_state(state)


def _event_age_seconds(event):
    raw = event.get("created_at")
    if not raw:
        return None
    try:
        created = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds()))
    except ValueError:
        return None


def execute(event, state):
    revalidate_terminal()
    if event["event_type"] == "OPEN":
        age = _event_age_seconds(event)
        if age is not None and age > MAX_STALE_OPEN_SECONDS:
            raise RuntimeError(f"Refusing stale OPEN event age={age}s")

    completed = state["completed"].get(event["event_key"])
    if completed:
        return completed["ticket"], completed["message"]

    master_ticket = event["master_ticket"]
    mapped = state["tickets"].get(master_ticket)
    if mapped and not find_position(mapped):
        recovered = find_position_by_master_ticket(master_ticket)
        mapped = str(recovered.ticket) if recovered else None
        if mapped:
            state["tickets"][master_ticket] = mapped
            save_state(state)

    if event["event_type"] == "OPEN":
        existing = find_position(mapped) if mapped else find_position_by_master_ticket(master_ticket)
        if existing is not None:
            ticket, message = str(existing.ticket), "already open"
            state["tickets"][master_ticket] = ticket
            remember_completed(event, state, ticket, message)
            return ticket, message
        result = send_checked(market_request(event))
        opened = find_position_by_master_ticket(master_ticket)
        subscriber_ticket = str(opened.ticket) if opened is not None else str(result.order or result.deal)
        state["tickets"][master_ticket] = subscriber_ticket
        message = "opened"
        remember_completed(event, state, subscriber_ticket, message)
        return subscriber_ticket, message

    if not mapped:
        recovered = find_position_by_master_ticket(master_ticket)
        if recovered is not None:
            mapped = str(recovered.ticket)
            state["tickets"][master_ticket] = mapped
            save_state(state)
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
        result = send_checked({
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position.ticket,
            "symbol": position.symbol,
            "sl": event.get("stop_loss") or 0.0,
            "tp": event.get("take_profit") or 0.0,
            "magic": MAGIC,
        })
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


def api(method, path, **kwargs):
    response = session.request(
        method,
        API + path,
        timeout=20,
        headers={"Authorization": f"Bearer {TOKEN}"},
        **kwargs,
    )
    if not response.ok:
        logger.error("CopyHub API error method=%s path=%s status=%s body=%s", method, path, response.status_code, response.text[:500])
    response.raise_for_status()
    return response.json()


def heartbeat(account, mode):
    symbols = mt5.symbols_get() or []
    info = next((item for item in symbols if item.trade_contract_size > 0 and item.volume_step > 0), None)
    if info is None:
        raise RuntimeError("No tradable symbol metadata is available for heartbeat")
    currency = str(account.currency).upper()
    unit = "USC" if currency in {"USC", "USCENT", "USCENTS", "CENT"} else "USD"
    result = api("POST", "/copyhub/v2/receiver/heartbeat", json={
        "account_number": str(account.login),
        "environment": mode,
        "server": str(account.server),
        "leverage": int(account.leverage or 0),
        "currency_unit": unit,
        "is_cent_account": unit == "USC",
        "contract_size": info.trade_contract_size,
        "min_lot": info.volume_min,
        "max_lot": info.volume_max,
        "lot_step": info.volume_step,
    })
    if str(result.get("master_account") or "") == str(account.login):
        raise RuntimeError("Safety stop: subscriber account resolved to itself as package master")
    return result


def run():
    account, mode = initialize_terminal()
    state, last_heartbeat = load_state(), 0.0
    recover_state_from_terminal(state)
    logger.info("subscriber copier ready account=%s mode=%s", account.login, mode)

    while True:
        try:
            account, mode = revalidate_terminal()
            if time.time() - last_heartbeat >= 30:
                hb = heartbeat(account, mode)
                last_heartbeat = time.time()
                logger.info(
                    "heartbeat package=%s master=%s paused=%s active=%s",
                    hb.get("package"), hb.get("master_account"), hb.get("paused"), hb.get("active"),
                )

            if not health.can_execute():
                logger.warning("local execution circuit open: %s", health.status())
                time.sleep(min(POLL_SECONDS, 2))
                continue

            response = api("GET", "/copyhub/v2/receiver/events?limit=50")
            if not response.get("execution_enabled"):
                time.sleep(POLL_SECONDS)
                continue

            for event in response.get("events", []):
                try:
                    ticket, message = execute(event, state)
                    api("POST", f"/copyhub/v2/receiver/deliveries/{event['delivery_id']}/ack", json={
                        "status": "ACKNOWLEDGED",
                        "receiver_ticket": ticket,
                        "message": message,
                    })
                    health.execution_ok()
                    logger.info("copied %s %s", event["event_type"], event["event_key"])
                except Exception as error:
                    health.execution_failed()
                    try:
                        api("POST", f"/copyhub/v2/receiver/deliveries/{event['delivery_id']}/ack", json={
                            "status": "FAILED",
                            "message": str(error)[:500],
                        })
                    except Exception as ack_error:
                        logger.error("failed to acknowledge copy failure: %s", ack_error)
                    logger.error("copy failed %s: %s health=%s", event.get("event_key"), error, health.status())
                    if not health.can_execute():
                        break
        except Exception as error:
            logger.error("copier loop error: %s", error)
            time.sleep(min(15, POLL_SECONDS * 5))
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()
