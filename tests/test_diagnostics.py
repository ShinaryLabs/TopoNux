import pytest

from toponux.collectors.diagnostics import inspect_ipv6, validate_target


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
