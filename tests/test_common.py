import subprocess

import pytest

from toponux.collectors import common


def _completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(args=["cmd"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_missing_binary_is_reported(monkeypatch):
    monkeypatch.setattr(common.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="not found"):
        common.run_text(["nope"])


def test_failed_command_reports_stderr(monkeypatch):
    monkeypatch.setattr(common.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(common.subprocess, "run", lambda *a, **k: _completed(stderr="permission denied", returncode=2))

    with pytest.raises(RuntimeError, match="permission denied"):
        common.run_json(["ip", "-j", "route"])


def test_empty_json_output_becomes_empty_list(monkeypatch):
    monkeypatch.setattr(common.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(common.subprocess, "run", lambda *a, **k: _completed(stdout=""))

    assert common.run_json(["ip", "-j", "route"]) == []


def test_json_null_becomes_empty_list(monkeypatch):
    monkeypatch.setattr(common.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(common.subprocess, "run", lambda *a, **k: _completed(stdout="null"))

    assert common.run_json(["ip", "-j", "route"]) == []


def test_run_text_returns_stdout_untouched(monkeypatch):
    monkeypatch.setattr(common.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(common.subprocess, "run", lambda *a, **k: _completed(stdout="raw rules\n"))

    assert common.run_text(["iptables-save"]) == "raw rules\n"
