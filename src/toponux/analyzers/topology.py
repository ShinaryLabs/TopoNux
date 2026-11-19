from __future__ import annotations

import ipaddress
import re

# Docker, libvirt and podman create bridges with recognizable generated names.
# User bridges such as "br-wan" must not be mistaken for container networks.
_VIRTUAL_BRIDGE_RE = re.compile(r"^(?:docker0|virbr\d*|podman\d*)$")
_DOCKER_BRIDGE_RE = re.compile(r"^br-[0-9a-f]{12}$")
_VETH_RE = re.compile(r"^veth[0-9a-z]+$")


def _is_virtual_bridge(iface: dict) -> bool:
    name = iface.get("ifname", "")
    return bool(_VIRTUAL_BRIDGE_RE.fullmatch(name) or _DOCKER_BRIDGE_RE.fullmatch(name))


def _is_veth(iface: dict) -> bool:
    return bool(_VETH_RE.fullmatch(iface.get("ifname", "")))


def _addresses(iface: dict) -> list[str]:
    return [
        f"{item['local']}/{item['prefixlen']}"
        for item in iface.get("addr_info", [])
        if item.get("local") and item.get("prefixlen") is not None
    ]


def _network_labels(iface: dict) -> list[str]:
    networks: list[str] = []
    for item in iface.get("addr_info", []):
        local, prefix = item.get("local"), item.get("prefixlen")
        if not local or prefix is None:
            continue
        try:
            network = str(ipaddress.ip_interface(f"{local}/{prefix}").network)
        except ValueError:
            continue
        if network not in networks:
            networks.append(network)
    return networks


def _is_docker_interface(name: str) -> bool:
    return name == "docker0" or bool(_DOCKER_BRIDGE_RE.fullmatch(name))


def _neighbor_state(entry: dict) -> str:
    state = entry.get("state", "")
    if isinstance(state, list):
        return " ".join(str(item) for item in state) or "UNKNOWN"
    return str(state) or "UNKNOWN"


def build_graph(snapshot: dict) -> dict:
    """Build a deliberately simplified overview; full data stays in detail tabs."""
    nodes: list[dict] = []
    edges: list[dict] = []
    interfaces = snapshot.get("interfaces", [])

    nodes.append(
        {
            "data": {
                "id": "host",
                "label": "Local machine",
                "kind": "host",
                "details": (
                    "Synthetic view of the network configuration. Select an element to inspect its properties."
                ),
            }
        }
    )

    # Physical / non-container interfaces with an address are shown individually.
    for iface in interfaces:
        name = iface.get("ifname", "unknown")
        if name == "lo" or _is_veth(iface) or _is_virtual_bridge(iface):
            continue
        addresses = _addresses(iface)
        if not addresses:
            continue
        state = iface.get("operstate", "UNKNOWN")
        node_id = f"if:{name}"
        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "label": f"{name}\n{addresses[0]}",
                    "kind": "interface",
                    "name": name,
                    "state": state,
                    "details": "\n".join(
                        [
                            f"Interface: {name}",
                            f"State: {state}",
                            f"MTU: {iface.get('mtu', '?')}",
                            f"MAC: {iface.get('address', '—')}",
                            "Addresses:",
                            *addresses,
                        ]
                    ),
                }
            }
        )
        edges.append({"data": {"id": f"host-{name}", "source": "host", "target": node_id, "label": "interface"}})

    # Docker / virtual bridges are represented as grouped networks, not as veth forests.
    for iface in interfaces:
        if not _is_virtual_bridge(iface) or iface.get("operstate") == "DOWN":
            continue
        name = iface.get("ifname", "bridge")
        networks = _network_labels(iface)
        addresses = _addresses(iface)
        state = iface.get("operstate", "UNKNOWN")
        node_id = f"bridge:{name}"
        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "label": f"{name}\n{', '.join(networks) if networks else 'no IP network'}",
                    "kind": "bridge",
                    "name": name,
                    "state": state,
                    "details": "\n".join(
                        [
                            f"Bridge: {name}",
                            f"State: {state}",
                            f"MTU: {iface.get('mtu', '?')}",
                            f"Member interfaces: {sum(1 for x in interfaces if x.get('master') == name)}",
                            "Addresses:",
                            *(addresses or ["None"]),
                        ]
                    ),
                }
            }
        )
        edges.append({"data": {"id": f"host-{name}", "source": "host", "target": node_id, "label": "virtual network"}})

    # ARP/NDP neighbours are shown as small leaf nodes attached to the interface
    # or bridge that reaches them. Docker networks stay flagged for the UI filter.
    parent_ids = {node["data"]["id"] for node in nodes}
    grouped: dict[tuple[str, str], dict] = {}
    raw_neighbors = snapshot.get("neighbors", [])
    for entry in raw_neighbors if isinstance(raw_neighbors, list) else []:
        dev, mac, dst = entry.get("dev"), entry.get("lladdr"), entry.get("dst")
        if not dev or not mac or not dst or dev == "lo" or _VETH_RE.fullmatch(dev):
            continue
        parent = f"if:{dev}" if f"if:{dev}" in parent_ids else f"bridge:{dev}"
        if parent not in parent_ids:
            continue
        record = grouped.setdefault((dev, mac), {"addresses": {"ip": [], "ip6": []}, "states": [], "parent": parent})
        family = "ip6" if ":" in dst else "ip"
        if dst not in record["addresses"][family]:
            record["addresses"][family].append(dst)
        state = _neighbor_state(entry)
        if state not in record["states"]:
            record["states"].append(state)

    for (dev, mac), record in grouped.items():
        ipv4, ipv6 = record["addresses"]["ip"], record["addresses"]["ip6"]
        addresses = [*ipv4, *ipv6]
        primary = addresses[0]
        family = "ip" if ipv4 else "ip6"
        docker = _is_docker_interface(dev)
        node_id = f"neighbor:{dev}:{mac}"
        more = f" (+{len(addresses) - 1})" if len(addresses) > 1 else ""
        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "label": f"{primary}{more}",
                    "kind": "neighbor",
                    "family": family,
                    "docker": docker,
                    "mac": mac,
                    "dev": dev,
                    "state": ", ".join(record["states"]),
                    "addresses": addresses,
                    "details": "\n".join(
                        [
                            f"Neighbor: {primary}",
                            "Addresses:",
                            *addresses,
                            f"MAC: {mac}",
                            f"Interface: {dev}",
                            f"State: {', '.join(record['states'])}",
                            "Source: ARP/NDP cache" + (" (container network)" if docker else ""),
                        ]
                    ),
                }
            }
        )
        edges.append(
            {
                "data": {
                    "id": f"neighbor-{dev}-{mac}",
                    "source": record["parent"],
                    "target": node_id,
                    "label": "docker" if docker else "neighbor",
                }
            }
        )

    # Show only the default route(s) in the overview. All routes remain in the Routes tab.
    # On-link defaults have no gateway: they are shown as a default route through their device.
    default_routes = []
    for family, routes in snapshot.get("routes", {}).items():
        for route in routes:
            if route.get("dst") == "default":
                default_routes.append((family, route))
    for index, (family, route) in enumerate(default_routes):
        gateway = route.get("gateway")
        dev = route.get("dev")
        hop = gateway or dev or "unknown"
        gw_id = f"gateway:{family}:{hop}:{index}"
        label = f"Gateway\n{gateway}" if gateway else f"Default route\n{dev or '—'}"
        details = "\n".join(
            [
                f"Gateway: {gateway or '— (on-link)'}",
                f"Family: {family}",
                f"Interface: {dev or '—'}",
                f"Table : {route.get('table', 'main')}",
                f"Metric: {route.get('metric', '—')}",
            ]
        )
        nodes.append(
            {
                "data": {
                    "id": gw_id,
                    "label": label,
                    "kind": "gateway",
                    "details": details,
                }
            }
        )
        target = f"if:{dev}" if dev and any(n["data"]["id"] == f"if:{dev}" for n in nodes) else "host"
        edges.append({"data": {"id": f"default-{index}", "source": target, "target": gw_id, "label": "default route"}})

    return {"nodes": nodes, "edges": edges}
