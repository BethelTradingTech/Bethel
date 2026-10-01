"""Offline checks for the MT5 first-sync history path."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


def connector_functions():
    tree = ast.parse(Path("connector/mt5_readonly_connector.py").read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"_history_rows", "sync_all_history"}]
    namespace = {"datetime": datetime, "timedelta": timedelta, "timezone": timezone,
                 "HISTORY_DAYS": 3650, "HISTORY_BATCH_SIZE": 500,
                 "last_history_sync": 0.0, "history_backfilled_for": None,
                 "time": SimpleNamespace(time=lambda: 123.0),
                 "logger": SimpleNamespace(info=lambda *args: None)}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "<connector>", "exec"), namespace)
    return namespace


def test_first_sync_imports_all_deals_in_bounded_batches_then_uses_recent_window():
    ns = connector_functions()
    deal = SimpleNamespace(entry=1, type=0, symbol="EURUSD", volume=0.1,
                           ticket=1, position_id=1, order=1, price=1.2,
                           profit=1, commission=0, swap=0, fee=0, time=1760000000)
    history = [SimpleNamespace(**{**vars(deal), "ticket": i}) for i in range(1, 5202)]
    windows, batches = [], []
    def fetch(start, end):
        windows.append((start, end))
        return history if end > datetime.now(timezone.utc) - timedelta(days=1) else []
    ns["mt5"] = SimpleNamespace(history_deals_get=fetch, last_error=lambda: "error",
                                  DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=2, DEAL_ENTRY_INOUT=3,
                                  DEAL_TYPE_BUY=0, DEAL_TYPE_BALANCE=4, DEAL_TYPE_CREDIT=5,
                                  DEAL_TYPE_BONUS=6, DEAL_TYPE_CORRECTION=7)
    ns["send"] = lambda batch, route: batches.append((batch, route))
    ns["sync_all_history"]("12345")
    assert windows[0][0] <= datetime.now(timezone.utc) - timedelta(days=3649)
    assert sum(len(batch["closed_deals"]) for batch, _ in batches) == 5201
    assert len(batches) == 11 and all(route == "history" for _, route in batches)
    assert all(len(batch["closed_deals"]) <= 500 and batch["account_number"] == "12345" for batch, _ in batches)
    windows.clear()
    ns["sync_all_history"]("12345")
    assert datetime.now(timezone.utc) - windows[0][0] < timedelta(days=8)


def test_failed_batch_retries_full_history_instead_of_marking_it_complete():
    ns = connector_functions()
    ns["mt5"] = SimpleNamespace(history_deals_get=lambda *args: None, last_error=lambda: "offline")
    try:
        ns["sync_all_history"]("12345")
    except RuntimeError:
        pass
    else:
        assert False, "MT5 failure must not mark backfill complete"
    assert ns["history_backfilled_for"] is None
