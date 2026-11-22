from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\.?$"
)

SCAN_MAX_HOSTS = 512
SCAN_WORKERS = 64
SCAN_PING_TIMEOUT = 2


def validate_target(target: str) -> str:
    target = target.strip()
    if not target or target.startswith("-") or any(c.isspace() for c in target):
        raise ValueError("Invalid target.")
    try:
        ipaddress.ip_address(target)
        return target
    except ValueError as exc:
        if not _HOST_RE.fullmatch(target):
            raise ValueError("Provide a valid IP address or DNS name.") from exc
        return target


def _run(command: list[str], timeout: int = 35) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("The diagnostic exceeded its time limit.") from exc


def route_lookup(target: str) -> dict:
    """Read the kernel's selected route for a destination."""
    binary = shutil.which("ip")
    if not binary:
        return {"available": False, "output": "ip command not found."}
    result = _run([binary, "route", "get", target], timeout=3)
    return {
        "available": result.returncode == 0,
        "output": (result.stdout + result.stderr).strip() or "No route returned.",
    }


def run_ping(target: str, count: int = 4) -> dict:
    target = validate_target(target)
    binary = shutil.which("ping")
    if not binary:
        return {"ok": False, "error": "ping is not installed."}
    result = _run([binary, "-n", "-c", str(count), "-W", "2", "--", target], timeout=count * 3 + 3)
    return {
        "ok": result.returncode == 0,
        "target": target,
        "count": count,
        "return_code": result.returncode,
        "reachable": result.returncode == 0,
        "route": route_lookup(target),
        "output": (result.stdout + result.stderr).strip(),
    }


def _ipv4_scan_networks(interfaces: list[dict]) -> list[dict]:
    """Return the distinct IPv4 subnets carried by non-down interfaces."""
    networks: dict[str, dict] = {}
    for iface in interfaces:
        ifname = iface.get("ifname")
        if not ifname or ifname == "lo" or iface.get("operstate") == "DOWN":
            continue
        for item in iface.get("addr_info", []):
            if item.get("family") != "inet":
                continue
            local, prefixlen = item.get("local"), item.get("prefixlen")
            if not local or prefixlen is None:
                continue
            try:
                interface = ipaddress.ip_interface(f"{local}/{prefixlen}")
            except ValueError:
                continue
            if not isinstance(interface, ipaddress.IPv4Interface):
                continue
            network = interface.network
            if network.is_loopback or network.is_link_local:
                continue
            key = str(network)
            entry = networks.get(key)
            if entry is None:
                entry = {"interface": ifname, "network": network, "locals": []}
                networks[key] = entry
            entry["locals"].append(interface.ip)
    return list(networks.values())


def _scan_targets(networks: list[dict], max_hosts: int) -> tuple[list[ipaddress.IPv4Address], bool]:
    """Enumerate usable hosts without materializing huge subnets."""
    targets: list[ipaddress.IPv4Address] = []
    local_ips = {address for entry in networks for address in entry["locals"]}
    for entry in networks:
        for host in entry["network"].hosts():
            if host in local_ips:
                continue
            if len(targets) >= max_hosts:
                return targets, True
            targets.append(host)
    return targets, False


def _ping_host(binary: str, host: ipaddress.IPv4Address) -> bool:
    """Send one ICMP echo without capturing output; return whether it answered."""
    try:
        result = subprocess.run(
            [binary, "-n", "-c", "1", "-W", "1", "--", str(host)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=SCAN_PING_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def scan_local_subnets(interfaces: list[dict], max_hosts: int | None = None) -> dict:
    """Ping every IPv4 host of the local subnets to populate the neighbour cache.

    This is an active probe: it sends one ICMP echo per host and lets the kernel
    update its ARP cache. It never configures an address, route or interface.
    """
    limit = SCAN_MAX_HOSTS if max_hosts is None else max_hosts
    networks = _ipv4_scan_networks(interfaces)
    summaries = [{"interface": entry["interface"], "network": str(entry["network"])} for entry in networks]
    binary = shutil.which("ping")
    if not binary:
        return {
            "available": False,
            "error": "ping is not installed.",
            "networks": summaries,
            "scanned": 0,
            "responsive": 0,
            "truncated": False,
        }

    targets, truncated = _scan_targets(networks, limit)
    started = time.monotonic()
    replies: list[bool] = []
    if targets:
        with ThreadPoolExecutor(max_workers=min(SCAN_WORKERS, len(targets))) as executor:
            replies = list(executor.map(lambda host: _ping_host(binary, host), targets))
    duration_ms = round((time.monotonic() - started) * 1000)
    responsive = sum(replies)
    message = f"Scanned {len(targets)} IPv4 host(s); {responsive} replied."
    if truncated:
        message += f" Limited to {limit} hosts."
    return {
        "available": True,
        "networks": summaries,
        "scanned": len(targets),
        "responsive": responsive,
        "truncated": truncated,
        "duration_ms": duration_ms,
        "message": message,
    }


def run_trace(target: str, max_hops: int = 20) -> dict:
    target = validate_target(target)
    tracepath = shutil.which("tracepath")
    traceroute = shutil.which("traceroute")
    if tracepath:
        command, tool = [tracepath, "-n", "-m", str(max_hops), target], "tracepath (UDP)"
    elif traceroute:
        command, tool = [traceroute, "-n", "-m", str(max_hops), "-w", "1", target], "traceroute (UDP)"
    else:
        return {
            "ok": False,
            "target": target,
            "error": "No tool available. Install tracepath (iputils-tracepath) or traceroute.",
        }
    result = _run(command, timeout=max_hops * 2 + 5)
    return {
        "ok": result.returncode == 0,
        "target": target,
        "tool": tool,
        "route": route_lookup(target),
        "return_code": result.returncode,
        "output": (result.stdout + result.stderr).strip(),
    }


def test_tcp_port(target: str, port: int, timeout: float = 2.0) -> dict:
    target = validate_target(target)
    started = time.monotonic()
    try:
        with socket.create_connection((target, port), timeout=timeout) as sock:
            elapsed = round((time.monotonic() - started) * 1000, 2)
            local = sock.getsockname()
            return {
                "target": target,
                "port": port,
                "protocol": "TCP",
                "reachable": True,
                "result": "connected",
                "latency_ms": elapsed,
                "route": route_lookup(target),
                "local_address": f"{local[0]}:{local[1]}",
                "interpretation": ("TCP connection established. The network path and the rules it crossed allowed it."),
            }
    except ConnectionRefusedError:
        result, explanation = (
            "refused",
            "The target answered with a TCP refusal (RST). The port may be closed "
            "or a device may reject the connection.",
        )
    except TimeoutError:
        result, explanation = (
            "timeout",
            "No answer within the time limit. Filtering, packet loss or a silent host are possible.",
        )
    except OSError as exc:
        result, explanation = "unreachable", f"Network failure: {exc}"
    return {
        "target": target,
        "port": port,
        "protocol": "TCP",
        "reachable": False,
        "result": result,
        "latency_ms": round((time.monotonic() - started) * 1000, 2),
        "route": route_lookup(target),
        "interpretation": explanation,
    }


_IPV6_TYPES = (
    (ipaddress.IPv6Network("::1/128"), "Loopback"),
    (ipaddress.IPv6Network("::/128"), "Unspecified"),
    (ipaddress.IPv6Network("::ffff:0:0/96"), "IPv4-mapped"),
    (ipaddress.IPv6Network("64:ff9b::/96"), "NAT64 well-known prefix"),
    (ipaddress.IPv6Network("64:ff9b:1::/48"), "NAT64 local-use prefix"),
    (ipaddress.IPv6Network("100::/64"), "Discard-only"),
    (ipaddress.IPv6Network("2001::/32"), "Teredo"),
    (ipaddress.IPv6Network("2001:2::/48"), "Benchmarking"),
    (ipaddress.IPv6Network("2001:20::/28"), "ORCHIDv2"),
    (ipaddress.IPv6Network("2001:db8::/32"), "Documentation"),
    (ipaddress.IPv6Network("2002::/16"), "6to4"),
    (ipaddress.IPv6Network("3fff::/20"), "Documentation"),
    (ipaddress.IPv6Network("fc00::/7"), "Unique local (ULA)"),
    (ipaddress.IPv6Network("fe80::/10"), "Link-local unicast"),
    (ipaddress.IPv6Network("ff00::/8"), "Multicast"),
)

_MULTICAST_SCOPES = {
    0: "reserved",
    1: "interface-local",
    2: "link-local",
    3: "realm-local",
    4: "admin-local",
    5: "site-local",
    8: "organization-local",
    14: "global",
    15: "reserved",
}

_WELL_KNOWN_MULTICAST = (
    (ipaddress.IPv6Network("ff02::1/128"), "All-nodes (link-local)"),
    (ipaddress.IPv6Network("ff02::2/128"), "All-routers (link-local)"),
    (ipaddress.IPv6Network("ff05::2/128"), "All-routers (site-local)"),
    (ipaddress.IPv6Network("ff02::1:ff00:0/104"), "Solicited-node"),
)


def _ipv6_type(address: ipaddress.IPv6Address) -> str:
    for network, label in _IPV6_TYPES:
        if address in network:
            return label
    return "Global unicast"


def _unicast_flags(address: ipaddress.IPv6Address, first_byte: int) -> list[dict]:
    bits = format(first_byte, "08b")
    return [
        {
            "name": "Prefix",
            "value": bits,
            "meaning": f"{_ipv6_type(address)} — first 8 address bits",
        }
    ]


def _multicast_flags(address: ipaddress.IPv6Address) -> tuple[list[dict], int]:
    second_byte = format(address.packed[1], "08b")
    scope_value = int(second_byte[4:], 2)
    flags = [
        {"name": "G", "value": "1", "meaning": "Multicast group"},
        {
            "name": "R",
            "value": second_byte[1],
            "meaning": "Rendezvous point" if second_byte[1] == "1" else "No rendezvous point",
        },
        {
            "name": "P",
            "value": second_byte[2],
            "meaning": "Not permanent" if second_byte[2] == "1" else "Permanent (IANA-assigned)",
        },
        {"name": "T", "value": second_byte[3], "meaning": "Transient" if second_byte[3] == "1" else "Not transient"},
        {
            "name": "Scope",
            "value": second_byte[4:],
            "meaning": _MULTICAST_SCOPES.get(scope_value, "unknown"),
        },
    ]
    return flags, scope_value


def inspect_ipv6(target: str) -> dict:
    """Describe an IPv6 address locally: type, scope, prefix and header flags.

    This is a pure computation. It sends no packet and queries no remote host.
    """
    value = target.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()
    if not value or any(character.isspace() for character in value):
        raise ValueError("Provide a single IPv6 address.")

    try:
        interface = ipaddress.ip_interface(value) if "/" in value else None
        address = interface.ip if interface is not None else ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError("Provide a valid IPv6 address, optionally with a /prefix.") from exc
    if not isinstance(address, ipaddress.IPv6Address):
        raise ValueError("This tool only inspects IPv6 addresses.")

    first_byte = address.packed[0]
    binary = format(first_byte, "08b")
    address_type = _ipv6_type(address)
    multicast = address.is_multicast
    flags, multicast_scope = _multicast_flags(address) if multicast else (_unicast_flags(address, first_byte), None)

    categories = [label for network, label in _IPV6_TYPES if address in network]
    well_known = [label for network, label in _WELL_KNOWN_MULTICAST if address in network]
    unscoped = ipaddress.IPv6Address(int(address))

    result = {
        "address": str(address),
        "compressed": address.compressed,
        "exploded": address.exploded,
        "type": address_type,
        "categories": categories,
        "well_known": well_known,
        "zone": address.scope_id,
        "prefixlen": interface.network.prefixlen if interface is not None else None,
        "network": str(interface.network) if interface is not None else None,
        "interface_id": f"{int(address) & ((1 << 64) - 1):016x}",
        "binary": " ".join(binary[index : index + 4] for index in range(0, 8, 4)),
        "flags": flags,
        "multicast_scope": _MULTICAST_SCOPES.get(multicast_scope) if multicast_scope is not None else None,
        "properties": {
            "global_unicast": not multicast and address_type == "Global unicast",
            "link_local": address.is_link_local,
            "unique_local": address in ipaddress.IPv6Network("fc00::/7"),
            "loopback": address.is_loopback,
            "unspecified": address.is_unspecified,
            "multicast": multicast,
            "reserved": address.is_reserved,
        },
        "reverse_dns": unscoped.reverse_pointer,
    }

    summary = address_type
    if address.scope_id:
        summary = f"{summary} on {address.scope_id}"
    result["summary"] = summary
    return result
