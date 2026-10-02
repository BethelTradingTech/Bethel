"""Offline checks for the MT5 first-sync history path."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


def connector_functions():
    tree = ast.parse(Path("connector/mt5_readonly_connector.py").read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"_history_rows", "sync_all_history", "snapshot_with_history", "_history_window", "_deal_utc"}]
    namespace = {"datetime": datetime, "timedelta": timedelta, "timezone": timezone,
                 "HISTORY_DAYS": 3650, "HISTORY_BATCH_SIZE": 500,
                 "last_history_sync": 0.0, "history_backfilled_for": None,
                 "time": SimpleNamespace(time=lambda: 123.0),
                 "logger": SimpleNamespace(info=lambda *args: None),
                 "_broker_offset": lambda raw: 0}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "<connector>", "exec"), namespace)
    return namespace


def test_first_sync_imports_all_deals_in_bounded_batches_then_uses_recent_window():
    ns = connector_functions()
    deal = SimpleNamespace(entry=1, type=0, symbol="EURUSD", volume=0.1,
                           ticket=1, position_id=1, order=1, price=1.2,
                           profit=1, commission=0, swap=0, fee=0, time=int(datetime.now(timezone.utc).timestamp())-60)
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
    assert datetime.now(timezone.utc) - windows[0][0] < timedelta(days=9)


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


def test_history_keeps_millisecond_order_and_supports_older_terminals():
    ns = connector_functions()
    ns["mt5"] = SimpleNamespace(DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=2,
        DEAL_ENTRY_INOUT=3, DEAL_TYPE_BUY=0, DEAL_TYPE_BALANCE=4,
        DEAL_TYPE_CREDIT=5, DEAL_TYPE_BONUS=6, DEAL_TYPE_CORRECTION=7)
    common = dict(entry=1, type=0, symbol="EURUSD", volume=0.1,
                  ticket=1, position_id=1, order=1, price=1.2,
                  profit=1, commission=0, swap=0, fee=0, time=1760000000)
    trade = SimpleNamespace(**common, time_msc=1760000000750)
    funding = SimpleNamespace(**{**common, "type": 4, "symbol": "", "volume": 0},
                              time_msc=1760000000250)
    deals, flows = ns["_history_rows"]([trade, funding])
    assert datetime.fromisoformat(flows[0]["occurred_at"]) < datetime.fromisoformat(deals[0]["closed_at"])
    assert datetime.fromisoformat(deals[0]["closed_at"]).microsecond == 750000
    legacy, _ = ns["_history_rows"]([SimpleNamespace(**common)])
    assert datetime.fromisoformat(legacy[0]["closed_at"]).microsecond == 0


def test_entry_commission_and_standalone_charge_are_not_funding_or_duplicate_exits():
    ns = connector_functions()
    ns["mt5"] = SimpleNamespace(DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=2,
        DEAL_ENTRY_INOUT=3, DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1,
        DEAL_TYPE_BALANCE=4, DEAL_TYPE_CREDIT=5, DEAL_TYPE_BONUS=6,
        DEAL_TYPE_CORRECTION=7, DEAL_TYPE_COMMISSION=8)
    common = dict(type=0, symbol="EURUSD", volume=.1, position_id=1,
                  order=1, price=1.2, swap=0, fee=0, time=1760000000)
    entry = SimpleNamespace(**common, ticket=10, entry=0, profit=0, commission=-2)
    exit = SimpleNamespace(**common, ticket=11, entry=1, profit=10, commission=-3)
    charge = SimpleNamespace(**{**common, "type": 8, "symbol": "", "volume": 0},
                             ticket=12, entry=0, profit=-1, commission=0)
    rows, flows = ns["_history_rows"]([entry, exit, charge])
    assert flows == []
    assert len(rows) == 3
    assert len({row["deal_ticket"] for row in rows}) == 3
    assert sum(row["profit"] + row["commission"] + row["swap"] + row["fee"] for row in rows) == 4
    assert sum(row["deal_type"] != "COST" for row in rows) == 1


def test_snapshot_includes_recent_history_and_retries_a_changing_balance():
    ns = connector_functions()
    captures = []
    def capture():
        captures.append(True)
        return {"account_number": "12345", "balance": 100,
                "observed_at": "2026-10-02T12:00:00+00:00"}
    accounts = iter([SimpleNamespace(login=12345, balance=101),
                     SimpleNamespace(login=12345, balance=100)])
    windows = []
    ns["snapshot"] = capture
    ns["_history_rows"] = lambda history: ([{"deal_ticket": "42"}], [{"deal_ticket": "43"}])
    ns["mt5"] = SimpleNamespace(history_deals_get=lambda start, end: windows.append((start, end)) or [],
                                 account_info=lambda: next(accounts))
    payload = ns["snapshot_with_history"]()
    assert len(captures) == 2
    assert payload["closed_deals"] == [{"deal_ticket": "42"}]
    assert payload["cash_flows"] == [{"deal_ticket": "43"}]
    assert windows[-1][1] == datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


def test_missing_recent_history_prevents_publishing_an_unexplained_balance():
    ns = connector_functions()
    ns["snapshot"] = lambda: {"account_number": "12345", "balance": 100,
                               "observed_at": "2026-10-02T12:00:00+00:00"}
    ns["mt5"] = SimpleNamespace(history_deals_get=lambda *args: None, last_error=lambda: "offline")
    import pytest
    with pytest.raises(RuntimeError, match="history unavailable"):
        ns["snapshot_with_history"]()


def test_broker_future_wall_time_is_imported_at_actual_utc_and_month_boundary():
    ns = connector_functions()
    ns["_broker_offset"] = lambda raw: 10800
    utc = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
    deal = SimpleNamespace(time=int(utc.timestamp())+10800,
                           time_msc=int(utc.timestamp()*1000)+10800000+750)
    ns["mt5"] = SimpleNamespace(history_deals_get=lambda start, end: [deal])
    rows = ns["_history_window"](utc-timedelta(minutes=1), utc+timedelta(minutes=1))
    assert rows == [deal]
    assert ns["_deal_utc"](deal) == "2026-09-30T23:30:00.750000+00:00"
    assert ns["_history_window"](utc+timedelta(minutes=1), utc+timedelta(minutes=2)) == []


def test_roboforex_historical_offset_changes_with_european_dst_without_account_ids():
    import os
    tree = ast.parse(Path("connector/mt5_readonly_connector.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_broker_offset")
    ns = dict(datetime=datetime, timedelta=timedelta, timezone=timezone,
              os=SimpleNamespace(getenv=lambda *args: ""),
              mt5=SimpleNamespace(account_info=lambda: SimpleNamespace(server="RoboForex-Pro")))
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<clock>", "exec"), ns)
    for month, offset in [(1,7200),(9,10800),(11,7200)]:
        assert ns["_broker_offset"](datetime(2026,month,15,tzinfo=timezone.utc).timestamp()) == offset
