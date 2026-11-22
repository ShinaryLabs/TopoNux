import subprocess

import pytest

import toponux.collectors.diagnostics as diagnostics
from toponux.collectors.diagnostics import inspect_ipv6, scan_local_subnets, validate_target


@pytest.mark.parametrize(
    "target",
    ["192.0.2.10", "2001:db8::1", "example.org", "host-1.lab.local", "a", "example.org."],
)
def test_validate_target_accepts_ip_and_dns(target):
    assert validate_target(f"  {target}  ") == target


@pytest.mark.parametrize(
    "target",
    ["", "   ", "-rf", "--help", "a b", "foo..bar", "a/b", "a;b", "a$(id)", "x" * 254],
)
def test_validate_target_rejects_unsafe_input(target):
    with pytest.raises(ValueError):
        validate_target(target)


class _CompletedProcess:
    def __init__(self, returncode: int):
        self.returncode = returncode


def test_scan_local_subnets_pings_hosts_and_counts_replies(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return _CompletedProcess(0 if command[-1].endswith(".9") else 1)

    monkeypatch.setattr(diagnostics.shutil, "which", lambda name: "/usr/bin/ping")
    monkeypatch.setattr(diagnostics.subprocess, "run", fake_run)
    interfaces = [
        {
            "ifname": "lo",
            "operstate": "UNKNOWN",
            "addr_info": [{"family": "inet", "local": "127.0.0.1", "prefixlen": 8}],
        },
        {
            "ifname": "eth0",
            "operstate": "UP",
            "addr_info": [{"family": "inet", "local": "192.0.2.10", "prefixlen": 29}],
        },
    ]

    result = scan_local_subnets(interfaces)

    assert result["available"] is True
    assert result["networks"] == [{"interface": "eth0", "network": "192.0.2.8/29"}]
    assert result["scanned"] == 5
    assert result["responsive"] == 1
    assert sorted(call[0][-1] for call in calls) == [
        "192.0.2.11",
        "192.0.2.12",
        "192.0.2.13",
        "192.0.2.14",
        "192.0.2.9",
    ]
    for command, kwargs in calls:
        assert command[:5] == ["/usr/bin/ping", "-n", "-c", "1", "-W"]
        assert command[-2] == "--"
        assert kwargs["timeout"] == diagnostics.SCAN_PING_TIMEOUT
        assert kwargs["stdout"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL
        assert "shell" not in kwargs


def test_scan_local_subnets_reports_missing_ping(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda name: None)

    result = scan_local_subnets(
        [{"ifname": "eth0", "addr_info": [{"family": "inet", "local": "192.0.2.10", "prefixlen": 24}]}]
    )

    assert result["available"] is False
    assert "ping" in result["error"]
    assert result["scanned"] == 0


def test_scan_local_subnets_skips_loopback_and_link_local(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda name: "/usr/bin/ping")
    interfaces = [
        {"ifname": "lo", "addr_info": [{"family": "inet", "local": "127.0.0.1", "prefixlen": 8}]},
        {"ifname": "eth0", "addr_info": [{"family": "inet", "local": "169.254.1.2", "prefixlen": 16}]},
    ]

    result = scan_local_subnets(interfaces)

    assert result["networks"] == []
    assert result["scanned"] == 0


def test_scan_local_subnets_truncates_large_networks(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda name: "/usr/bin/ping")
    monkeypatch.setattr(diagnostics.subprocess, "run", lambda *args, **kwargs: _CompletedProcess(1))
    interfaces = [
        {"ifname": "eth0", "operstate": "UP", "addr_info": [{"family": "inet", "local": "10.0.0.1", "prefixlen": 24}]}
    ]

    result = scan_local_subnets(interfaces, max_hosts=2)

    assert result["scanned"] == 2
    assert result["truncated"] is True
    assert "Limited to 2 hosts" in result["message"]


def test_inspect_link_local_ipv6_with_zone():
    result = inspect_ipv6("fe80::1%eth0")

    assert result["type"] == "Link-local unicast"
    assert result["zone"] == "eth0"
    assert result["properties"]["link_local"] is True
    assert result["properties"]["global_unicast"] is False
    assert {flag["name"] for flag in result["flags"]} == {"Prefix"}
    assert result["summary"] == "Link-local unicast on eth0"


def test_inspect_global_unicast_shows_prefix_flag():
    result = inspect_ipv6("2001:db8::1")

    flags = {flag["name"]: flag["value"] for flag in result["flags"]}

    assert result["type"] == "Documentation"
    assert flags == {"Prefix": "00100000"}


def test_inspect_multicast_flags_and_scope():
    result = inspect_ipv6("ff02::1")

    flags = {flag["name"]: flag["value"] for flag in result["flags"]}

    assert result["type"] == "Multicast"
    assert result["multicast_scope"] == "link-local"
    assert "All-nodes (link-local)" in result["well_known"]
    assert flags["G"] == "1"
    assert flags["Scope"] == "0010"


def test_inspect_accepts_prefix_and_detects_ula():
    result = inspect_ipv6("fd12:3456::1/64")

    assert result["type"] == "Unique local (ULA)"
    assert result["prefixlen"] == 64
    assert result["network"] == "fd12:3456::/64"
    assert result["properties"]["unique_local"] is True


def test_inspect_accepts_bracketed_address():
    assert inspect_ipv6("[2001:db8::1]")["compressed"] == "2001:db8::1"


def test_reverse_dns_ignores_zone():
    reverse = inspect_ipv6("fe80::1%eth0")["reverse_dns"]

    assert reverse.endswith(".ip6.arpa")
    assert "%" not in reverse


@pytest.mark.parametrize("target", ["192.0.2.1", "not-an-address", "", "fe80::1%eth0/64 extra"])
def test_inspect_rejects_non_ipv6_or_unsafe_input(target):
    with pytest.raises(ValueError):
        inspect_ipv6(target)
