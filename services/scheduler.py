"""Bethel Trading Technologies - local MT5 snapshot and history scheduler."""

import time
from datetime import datetime

from api.services.trade_importer import import_mt5_history
from services.equity_collector import EquityCollector


class EquityScheduler:
    def __init__(self):
        self.collector = EquityCollector()
        self.running = False

    def run_once(self):
        print(f"[{datetime.now()}] Collecting equity snapshot...")
        snapshot_result = self.collector.collect()
        print(snapshot_result)

        if snapshot_result.get("status") == "success":
            print(f"[{datetime.now()}] Importing closed MT5 trades...")
            history_result = import_mt5_history()
            print(history_result)

    def start(self, interval_seconds=3600):
        self.running = True
        print("Bethel Trading Technologies Equity Scheduler Started")

        while self.running:
            try:
                self.run_once()
            except Exception as exc:
                print("Scheduler Error:", exc)
            time.sleep(interval_seconds)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    EquityScheduler().start(interval_seconds=3600)
