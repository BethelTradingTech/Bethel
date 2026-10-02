"""Exercise the production calculator against an isolated signed ledger."""
import ast
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from api.services.ledger_reconciliation import reconciliation_is_acceptable, resolve_opening_balance


def calculator(snapshot_at, balance, deals, flows):
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
        db.add_all(Deal(account_number="12345", closed_at=row[0], profit=row[1],
                       deal_type=row[2] if len(row) > 2 else "BUY") for row in deals)
        db.add_all(Flow(account_number="12345", occurred_at=at, amount=value) for at, value in flows)
        db.commit()
    tree = ast.parse(Path("api/services/account_risk_profile.py").read_text())
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
    ns = dict(__name__="builtins", defaultdict=defaultdict, dataclass=dataclass, datetime=datetime,
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
    assert result["closed_deals"] == result["cash_flow_events"] == 1
    assert result["total_realized_return_percent"] == 10


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
    assert isinstance(cutoff, ast.Constant) and cutoff.value is False
