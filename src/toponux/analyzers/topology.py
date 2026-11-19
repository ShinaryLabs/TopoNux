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
