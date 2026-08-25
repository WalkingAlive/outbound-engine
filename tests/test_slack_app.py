import pytest


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """cli.py's commands call Storage() with no args, which defaults to the
    real DB_PATH resolved at import time - that default binds too early for
    an env-var override to reach it, so patch the `Storage` name cli.py
    actually calls instead.
    """
    from outbound_engine.storage import Storage as RealStorage

    def factory(*args, **kwargs):
        kwargs.setdefault("db_path", tmp_path / "test.db")
        return RealStorage(*args, **kwargs)

    monkeypatch.setattr("outbound_engine.cli.Storage", factory)


def test_run_cli_add_and_list_target():
    from outbound_engine.slack_app import _run_cli

    out = _run_cli(["add-target", "--name", "Jane Doe", "--type", "person"])
    assert "Tracking Jane Doe" in out

    out = _run_cli(["list-targets"])
    assert "Jane Doe" in out


def test_run_cli_unknown_command_reports_error_not_crash():
    from outbound_engine.slack_app import _run_cli

    out = _run_cli(["not-a-real-command"])
    assert isinstance(out, str)


def test_run_cli_help_via_argparse():
    from outbound_engine.slack_app import _run_cli

    out = _run_cli(["--help"])
    assert "usage" in out.lower()
