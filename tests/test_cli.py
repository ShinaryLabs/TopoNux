import pytest
from typer.testing import CliRunner

from toponux import cli

runner = CliRunner()


@pytest.fixture
def started(monkeypatch):
    """Record the server launch instead of opening a port."""
    calls = []
    monkeypatch.setenv("TOPONUX_ALLOWED_HOSTS", "")
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))
    monkeypatch.setattr(cli.os, "geteuid", lambda: 1000)
    return calls


def test_remote_address_needs_explicit_flag(started):
    result = runner.invoke(cli.app, ["--host", "0.0.0.0"])

    assert result.exit_code == 1
    assert started == []


def test_allowed_hosts_are_exported(started):
    result = runner.invoke(
        cli.app, ["--host", "0.0.0.0", "--allow-remote", "--allowed-host", "server.example", "--no-browser"]
    )

    assert result.exit_code == 0
    assert cli.os.environ["TOPONUX_ALLOWED_HOSTS"] == "0.0.0.0,server.example"
    assert started[0]["host"] == "0.0.0.0"


def test_root_gets_a_warning_and_no_browser(started, monkeypatch):
    monkeypatch.setattr(cli.os, "geteuid", lambda: 0)
    monkeypatch.setattr("threading.Timer", lambda *args: pytest.fail("browser must not open as root"))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 0
    assert "running as root" in result.output
