"""Exercise the production calculator against an isolated signed ledger."""
import ast
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from api.services.ledger_reconciliation import reconciliation_is_acceptable, resolve_opening_balance


def calculator(snapshot_at, balance, deals, flows, extra_snapshots=()):
    base = declarative_base()
    class Snapshot(base):
        __tablename__ = "snapshots"
        id = Column(Integer, primary_key=True)
        account_number = Column(String)
        timestamp = Column(DateTime)
        balance = Column(Float)
    class Deal(base):
        __tablename__ = "deals"
        id = Column(Integer, primary_key=True)
        account_number = Column(String)
        closed_at = Column(DateTime)
        profit = Column(Float)
        deal_type = Column(String, default="BUY")
        commission = Column(Float, default=0)
        swap = Column(Float, default=0)
        fee = Column(Float, default=0)
    class Flow(base):
        __tablename__ = "flows"
        id = Column(Integer, primary_key=True)
        account_number = Column(String)
        occurred_at = Column(DateTime)
        amount = Column(Float)
    engine = create_engine("sqlite://")
    base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        db.add(Snapshot(account_number="12345", timestamp=snapshot_at, balance=balance))
        db.add_all(Snapshot(account_number="12345", timestamp=at, balance=value)
                   for at, value in extra_snapshots)
        db.add_all(Deal(account_number="12345", closed_at=row[0], profit=row[1],
                       deal_type=row[2] if len(row) > 2 else "BUY") for row in deals)
        db.add_all(Flow(account_number="12345", occurred_at=at, amount=value) for at, value in flows)
        db.commit()
    tree = ast.parse(Path("api/services/account_risk_profile.py").read_text())
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
    ns = dict(__name__="builtins", defaultdict=defaultdict, dataclass=dataclass, datetime=datetime, timezone=timezone,
              timedelta=timedelta, math=math, np=np, SessionLocal=sessions,
              EquitySnapshot=Snapshot, ConnectorDeal=Deal, ConnectorCashFlow=Flow,
              TRADING_DAYS_PER_YEAR=252, reconciliation_is_acceptable=reconciliation_is_acceptable,
              resolve_opening_balance=resolve_opening_balance)
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
    exec(compile(module, "<profile>", "exec"), ns)
    return ns["get_account_risk_profile"]


def test_weekend_trade_contributes_to_month_and_total():
    calculate = calculator(datetime(2026, 9, 28), 110,
                           [(datetime(2026, 9, 26, 12), 10)],
                           [(datetime(2026, 9, 25), 100)])
    result = calculate("12345")
    assert result["monthly_returns"] == [{"period": "2026-09", "return_percent": 10}]
    assert result["total_realized_return_percent"] == 10
    assert result["trading_days"] == 1


@pytest.mark.parametrize("as_of", [None, datetime(2026, 10, 1)])
def test_history_newer_than_snapshot_cannot_change_opening_or_return(as_of):
    calculate = calculator(datetime(2026, 9, 30, 12), 110,
                           [(datetime(2026, 9, 30, 10), 10),
                            (datetime(2026, 9, 30, 13), -80)],
                           [(datetime(2026, 9, 1), 100),
                            (datetime(2026, 9, 30, 14), 50)])
    result = calculate("12345", as_of=as_of)
    assert result["status"] == "available"
    assert result["opening_balance"] == 0
    assert result["closed_deals"] == result["cash_flow_events"] == (1 if as_of is None else 2)
    assert result["total_realized_return_percent"] == (10 if as_of is None else -70)


def test_partial_loss_then_funding_and_recovery_retains_existing_compounding():
    calculate = calculator(datetime(2026, 9, 30), 150,
                           [(datetime(2026, 9, 10), -50), (datetime(2026, 9, 20), 50)],
                           [(datetime(2026, 9, 1), 100), (datetime(2026, 9, 15), 50)])
    assert calculate("12345")["total_realized_return_percent"] == -25


@pytest.mark.parametrize("ending, expected", [(30, 200), (40, 300), (50, 400)])
def test_total_loss_restarts_from_new_funding(ending, expected):
    calculate = calculator(datetime(2026, 9, 30), ending,
                           [(datetime(2026, 9, 10), -20), (datetime(2026, 9, 20), ending - 10)],
                           [(datetime(2026, 9, 5), 20), (datetime(2026, 9, 15), 10)])
    result = calculate("12345")
    assert result["status"] == "available"
    assert result["monthly_returns"] == [{"period": "2026-09", "return_percent": expected}]
    assert result["performance_start"] == "2026-09-15"
    assert result["funding_restart_count"] == 1


def test_full_withdrawal_does_not_restart():
    calculate = calculator(datetime(2026, 9, 30), 20,
        [(datetime(2026, 9, 5), 10), (datetime(2026, 9, 20), 10)],
        [(datetime(2026, 9, 1), 100), (datetime(2026, 9, 10), -110),
         (datetime(2026, 9, 15), 10)])
    result = calculate("12345")
    assert result["funding_restart_count"] == 0
    assert result["total_realized_return_percent"] == 120


def test_restart_preserves_previous_months_and_negative_balance_is_paid_first():
    calculate = calculator(datetime(2026, 9, 30), 20,
        [(datetime(2026, 8, 10), 10), (datetime(2026, 8, 20), -112),
         (datetime(2026, 9, 20), 10)],
        [(datetime(2026, 8, 1), 100), (datetime(2026, 9, 15), 12)])
    result = calculate("12345")
    assert result["monthly_returns"] == [
        {"period": "2026-08", "return_percent": -100},
        {"period": "2026-09", "return_percent": 100}]
    assert result["total_realized_return_percent"] == 100


def test_admin_ytd_uses_restart_but_keeps_previous_month_cells():
    tree = ast.parse(Path("api/admin_master_performance.py").read_text())
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_yearly_returns")
    ns = dict(defaultdict=defaultdict, _round=lambda value: round(value, 2))
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<yearly>", "exec"), ns)
    rows = [{"month": "2026-08", "return_percent": -100},
            {"month": "2026-09", "return_percent": 100}]
    result = ns["_yearly_returns"](rows, "2026-09-15")
    assert result[0]["months"] == {"8": -100, "9": 100}
    assert result[0]["ytd_return_percent"] == 100


def test_costs_reduce_return_without_counting_as_completed_trades():
    calculate = calculator(datetime(2026, 9, 30), 104,
        [(datetime(2026, 9, 2), -2, "COST"), (datetime(2026, 9, 3), 7),
         (datetime(2026, 9, 4), -1, "COST")], [(datetime(2026, 9, 1), 100)])
    result = calculate("12345")
    assert result["total_realized_return_percent"] == 4
    assert result["closed_deals"] == result["trading_days"] == 1


def test_cost_schema_accepts_zero_dimensions_but_trade_schema_stays_strict():
    from pydantic import BaseModel, Field, ValidationError, model_validator
    tree = ast.parse(Path("api/mt5_ingest/routes.py").read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ClosedDeal")
    ns = dict(BaseModel=BaseModel, Field=Field, model_validator=model_validator, datetime=datetime)
    exec(compile(ast.Module(body=[cls], type_ignores=[]), "<schema>", "exec"), ns)
    data = dict(deal_ticket="1", position_id="0", order_id="0", symbol="LEDGER",
                deal_type="COST", volume=0, price=0, profit=-2, closed_at=datetime(2026, 9, 1))
    assert ns["ClosedDeal"](**data).profit == -2
    with pytest.raises(ValidationError):
        ns["ClosedDeal"](**{**data, "deal_type": "BUY"})
    with pytest.raises(ValidationError):
        ns["ClosedDeal"](**{**data, "volume": 1})


def test_every_account_uses_the_public_monthly_reporting_policy():
    tree = ast.parse(Path("api/admin_master_performance.py").read_text())
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "master_performance")
    call = next(node for node in ast.walk(fn) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == "_profile_return_report")
    cutoff = next(kw.value for kw in call.keywords if kw.arg == "lock_completed_months")
    assert isinstance(cutoff, ast.Constant) and cutoff.value is True


def test_unsynced_october_balance_cannot_become_opening_capital_or_erase_restart():
    calculate = calculator(datetime(2026, 10, 2), 45,
        [(datetime(2026, 9, 10), -20), (datetime(2026, 9, 20), 30)],
        [(datetime(2026, 9, 5), 20), (datetime(2026, 9, 15), 10)],
        extra_snapshots=[(datetime(2026, 9, 30, 23, 59), 40)])
    live = calculate("12345")
    assert live["status"] == "not_available"
    assert live["reason"] == "current_month_ledger_unreconciled"
    finalized = calculate.__globals__["get_finalized_account_profile"](
        "12345", now=datetime(2026, 10, 2))
    assert finalized["monthly_returns"] == [{"period": "2026-09", "return_percent": 300}]
    assert finalized["funding_restart_count"] == 1


def test_each_completed_month_uses_its_own_balance_cutoff():
    # An unrelated later discrepancy must not rewrite August's opening capital.
    calculate = calculator(datetime(2026, 10, 31, 23, 59), 135,
        [(datetime(2026, 8, 5), 10), (datetime(2026, 9, 5), 10),
         (datetime(2026, 10, 5), 10)], [(datetime(2026, 8, 1), 100)],
        extra_snapshots=[(datetime(2026, 8, 31, 23, 59), 110),
                         (datetime(2026, 9, 30, 23, 59), 120)])
    finalized = calculate.__globals__["get_finalized_account_profile"](
        "12345", now=datetime(2026, 11, 2))
    assert finalized["monthly_returns"][:2] == [
        {"period": "2026-08", "return_percent": 10},
        {"period": "2026-09", "return_percent": 9.0909}]


def test_account_connected_later_keeps_earlier_broker_history():
    calculate = calculator(datetime(2026, 10, 2), 125,
        [(datetime(2026, 8, 5), 10), (datetime(2026, 9, 5), 10),
         (datetime(2026, 10, 1), 5)], [(datetime(2026, 8, 1), 100)])
    finalized = calculate.__globals__["get_finalized_account_profile"](
        "12345", now=datetime(2026, 10, 2))
    assert finalized["status"] == "available"
    assert finalized["monthly_returns"] == [
        {"period": "2026-08", "return_percent": 10},
        {"period": "2026-09", "return_percent": 9.0909}]


def test_later_funding_is_removed_when_reconstructing_a_missing_month_end():
    calculate = calculator(datetime(2026, 10, 2), 170,
        [(datetime(2026, 9, 5), 20)],
        [(datetime(2026, 9, 1), 100), (datetime(2026, 10, 1), 50)])
    historical = calculate("12345", as_of=datetime(2026, 10, 1))
    assert historical["monthly_returns"] == [{"period": "2026-09", "return_percent": 20}]
    assert historical["opening_balance"] == 0


def test_complete_loss_month_remains_visible_after_next_month_restart():
    calculate = calculator(datetime(2026, 10, 31, 23, 59), 20,
        [(datetime(2026, 9, 10), -20), (datetime(2026, 10, 20), 10)],
        [(datetime(2026, 9, 5), 20), (datetime(2026, 10, 15), 10)],
        extra_snapshots=[(datetime(2026, 9, 30, 23, 59), 0)])
    finalized = calculate.__globals__["get_finalized_account_profile"](
        "12345", now=datetime(2026, 11, 2))
    assert finalized["monthly_returns"] == [
        {"period": "2026-09", "return_percent": -100},
        {"period": "2026-10", "return_percent": 100}]
    assert finalized["funding_restart_count"] == 1


def test_funded_month_without_closed_trades_is_zero_and_does_not_block_later_history():
    calculate = calculator(datetime(2026, 9, 30, 23, 59), 110,
        [(datetime(2026, 9, 5), 10)], [(datetime(2026, 8, 31), 100)])
    finalized = calculate.__globals__["get_finalized_account_profile"](
        "12345", now=datetime(2026, 10, 2))
    assert finalized["status"] == "available"
    assert finalized["monthly_returns"] == [
        {"period": "2026-08", "return_percent": 0},
        {"period": "2026-09", "return_percent": 10}]
