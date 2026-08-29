from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v2_routing_is_package_controlled_not_subscriber_selected():
    text = source("api/copyhub/package_router.py")
    assert 'router = APIRouter(prefix="/copyhub/v2"' in text
    assert "PackageMasterRoute" in text
    assert '"subscriber_master_selection": False' in text
    assert "ClientOnboarding.plan_id" in text
    assert "terminal_registry_id" in text


def test_v2_master_event_is_bound_to_registered_connector_and_account():
    text = source("api/copyhub/package_router.py")
    assert "MasterTerminalRegistry.connector_id == connector_id" in text
    assert "MasterTerminalRegistry.account_number == data.account_number" in text
    assert "MasterTerminalRegistry.subscriber_id.is_(None)" in text
    assert "PackageMasterRoute.terminal_registry_id == registry.id" in text


def test_receiver_route_changes_fail_closed():
    text = source("api/copyhub/package_router.py")
    assert "receiver.channel_id = channel.id" in text
    assert "receiver.paused = True" in text
    assert "Package master terminal is offline or stale" in text
    assert "A LIVE receiver cannot be activated against a DEMO package master" in text


def test_diagnostics_only_auto_remediate_fail_closed_states():
    text = source("api/copyhub/diagnostics.py")
    assert '"fail_closed_no_trade_mutation"' in text
    assert "MASTER_TELEMETRY_STALE" in text
    assert "RECEIVER_ROUTE_MISMATCH" in text
    assert "REPEATED_DELIVERY_FAILURES" in text
    assert "receiver.paused = True" in text
    assert "channel.globally_paused = True" in text
    assert "order_send" not in text


def test_local_copier_has_idempotency_and_failure_circuit_breaker():
    text = source("connector/mt5_subscriber_copier.py")
    assert "LocalHealthReasoner" in text
    assert "FAILURE_CIRCUIT_THRESHOLD" in text
    assert 'state["completed"]' in text
    assert "mt5.order_check" in text
    assert "mt5.order_send" in text
    assert '"/copyhub/v2/receiver/events?limit=50"' in text


def test_master_connectors_support_explicit_mt5_terminal_paths():
    telemetry = source("connector/mt5_readonly_connector.py")
    publisher = source("connector/mt5_master_event_publisher.py")
    assert "BETHEL_MT5_TERMINAL_PATH" in telemetry
    assert "mt5.initialize(path=TERMINAL_PATH)" in telemetry
    assert "BETHEL_MT5_TERMINAL_PATH" in publisher
    assert "mt5.initialize(path=TERMINAL_PATH)" in publisher


def test_v1_guard_remains_in_place_while_v2_is_separate():
    main = source("main.py")
    production = source("render_app.py")
    assert '"/copyhub/v1/"' in main
    assert "package_copyhub_router" in production
    assert 'PACKAGE_COPIER_STATUS_PATH = "/copyhub/v2/admin/status"' in production
