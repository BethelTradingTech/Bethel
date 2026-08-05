from types import SimpleNamespace

from api.copytrading.dashboard_routes import current_receiver_mode


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Db:
    def __init__(self, rows):
        self._rows = rows

    def query(self, _model):
        return _Query(self._rows)


def receiver(environment: str, live_authorized: bool = False):
    return SimpleNamespace(
        environment=environment,
        live_authorized=live_authorized,
    )


def test_mode_is_demo_when_copy_hub_receivers_are_demo_accounts():
    assert current_receiver_mode(_Db([receiver("DEMO"), receiver("DEMO")])) == (
        "DEMO",
        2,
        0,
    )


def test_mode_is_live_only_for_authorized_live_receivers():
    assert current_receiver_mode(_Db([receiver("LIVE", True)])) == (
        "LIVE",
        0,
        1,
    )


def test_mode_is_mixed_when_demo_and_authorized_live_receivers_exist():
    assert current_receiver_mode(
        _Db([receiver("DEMO"), receiver("LIVE", True)])
    ) == ("MIXED", 1, 1)


def test_mode_never_defaults_to_paper():
    assert current_receiver_mode(_Db([]))[0] == "NO_RECEIVERS"
    assert current_receiver_mode(_Db([receiver("LIVE", False)]))[0] == "NOT_AUTHORIZED"
