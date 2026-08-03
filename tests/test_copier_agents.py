import importlib
import sys
from types import SimpleNamespace


sys.modules.setdefault("MetaTrader5", SimpleNamespace())
sys.modules.setdefault("requests", SimpleNamespace(Session=lambda: SimpleNamespace()))


def test_master_change_detection_open_modify_partial_and_close():
    publisher = importlib.import_module("connector.mt5_master_event_publisher")
    base = {"symbol": "EURUSD", "direction": "BUY", "price": 1.1}
    previous = {
        "1": {**base, "master_ticket": "1", "volume": 1.0, "stop_loss": 1.0, "take_profit": 1.2},
        "2": {**base, "master_ticket": "2", "volume": 0.5, "stop_loss": 1.0, "take_profit": 1.2},
    }
    current = {
        "1": {**base, "master_ticket": "1", "volume": 0.6, "stop_loss": 1.05, "take_profit": 1.2},
        "3": {**base, "master_ticket": "3", "volume": 0.2, "stop_loss": 1.0, "take_profit": 1.2},
    }
    events = publisher.changes(previous, current)
    assert [(event["master_ticket"], event["event_type"]) for event in events] == [
        ("1", "PARTIAL_CLOSE"), ("1", "MODIFY"), ("3", "OPEN"), ("2", "CLOSE")
    ]
    assert events[0]["volume"] == 0.4


def test_subscriber_copier_refuses_master_account(monkeypatch):
    copier = importlib.import_module("connector.mt5_subscriber_copier")
    monkeypatch.setattr(copier, "TOKEN", "t" * 64)
    monkeypatch.setattr(copier, "EXPECTED_ACCOUNT", copier.MASTER_ACCOUNT)
    try:
        copier.initialize_terminal()
    except RuntimeError as error:
        assert "master account" in str(error)
    else:
        raise AssertionError("Copier did not reject the master account")
