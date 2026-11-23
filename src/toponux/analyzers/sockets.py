from __future__ import annotations

import ipaddress


def _split_endpoint(value: str) -> tuple[str, int | None]:
    """Split an ``ss`` endpoint such as ``[::]:443`` or ``192.0.2.1%eth0:22``."""
    address, separator, port = value.rpartition(":")
    if not separator:
        return value, None
    if address.startswith("[") and address.endswith("]"):
        address = address[1:-1]
    address = address.split("%", 1)[0]
    try:
        port_number = int(port)
    except ValueError:
        port_number = None
    return address, port_number


def _local_addresses(interfaces: list[dict] | None) -> set[str]:
    addresses: set[str] = set()
    for iface in interfaces or []:
        for item in iface.get("addr_info", []):
            local = item.get("local")
            if local:
                addresses.add(str(local).split("%", 1)[0])
    return addresses


def _is_third_party(address: str, local_addresses: set[str]) -> bool:
    if not address or address in {"*", "0.0.0.0", "::"} or address in local_addresses:
        return False
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (parsed.is_loopback or parsed.is_unspecified or parsed.is_multicast)


def _is_listener(netid: str, state: str, local_port: int | None) -> bool:
    if state == "LISTEN":
        return True
    return netid == "udp" and state == "UNCONN" and local_port is not None


def normalize_sockets(entries: list[dict] | None, interfaces: list[dict] | None, error: str | None = None) -> dict:
    """Split raw ``ss`` records into listening ports and remote connections."""
    if error:
        return {"available": False, "error": error, "listeners": [], "connections": []}

    listeners: list[dict] = []
    connections: list[dict] = []
    local_addresses = _local_addresses(interfaces)
    for entry in entries or []:
        netid = str(entry.get("netid", "")).lower()
        state = str(entry.get("state", "")).upper()
        if netid not in {"tcp", "udp"}:
            continue
        local_address, local_port = _split_endpoint(str(entry.get("local", "")))
        peer_address, peer_port = _split_endpoint(str(entry.get("peer", "")))
        record = {
            "protocol": netid,
            "state": state,
            "local_address": local_address,
            "local_port": local_port,
            "peer_address": peer_address,
            "peer_port": peer_port,
            "processes": entry.get("processes") or [],
        }
        if _is_listener(netid, state, local_port):
            listeners.append(record)
        elif state in {"ESTAB", "ESTABLISHED"} and _is_third_party(peer_address, local_addresses):
            connections.append(record)

    listeners.sort(key=lambda item: (item["protocol"], item["local_port"] or 0, item["local_address"]))
    connections.sort(
        key=lambda item: (
            item["protocol"],
            item["peer_address"],
            item["peer_port"] or 0,
            item["local_port"] or 0,
        )
    )
    return {"available": True, "listeners": listeners, "connections": connections}
