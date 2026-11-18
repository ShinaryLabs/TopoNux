from __future__ import annotations

import ipaddress


def _is_virtual_bridge(iface: dict) -> bool:
    name = iface.get("ifname", "")
    return name == "docker0" or name.startswith(("br-", "virbr", "podman"))


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
                "label": "Machine locale",
                "kind": "host",
                "details": (
                    "Vue synthétique de la configuration réseau. Sélectionne un élément pour consulter ses propriétés."
                ),
            }
        }
    )

    # Physical / non-container interfaces with an address are shown individually.
    for iface in interfaces:
        name = iface.get("ifname", "unknown")
        if name == "lo" or name.startswith("veth") or _is_virtual_bridge(iface):
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
                            f"Interface : {name}",
                            f"État : {state}",
                            f"MTU : {iface.get('mtu', '?')}",
                            f"MAC : {iface.get('address', '—')}",
                            "Adresses :",
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
                    "label": f"{name}\n{', '.join(networks) if networks else 'sans réseau IP'}",
                    "kind": "bridge",
                    "name": name,
                    "state": state,
                    "details": "\n".join(
                        [
                            f"Bridge : {name}",
                            f"État : {state}",
                            f"MTU : {iface.get('mtu', '?')}",
                            f"Interfaces esclaves : {sum(1 for x in interfaces if x.get('master') == name)}",
                            "Adresses :",
                            *(addresses or ["Aucune"]),
                        ]
                    ),
                }
            }
        )
        edges.append({"data": {"id": f"host-{name}", "source": "host", "target": node_id, "label": "réseau virtuel"}})

    # Show only the default gateway(s) in the overview. All routes remain in the Routes tab.
    default_routes = []
    for family, routes in snapshot.get("routes", {}).items():
        for route in routes:
            if route.get("dst") == "default" and route.get("gateway"):
                default_routes.append((family, route))
    for index, (family, route) in enumerate(default_routes):
        gateway = route["gateway"]
        gw_id = f"gateway:{family}:{gateway}:{index}"
        dev = route.get("dev")
        details = "\n".join(
            [
                f"Passerelle : {gateway}",
                f"Famille : {family}",
                f"Interface : {dev or '—'}",
                f"Table : {route.get('table', 'main')}",
                f"Métrique : {route.get('metric', '—')}",
            ]
        )
        nodes.append(
            {
                "data": {
                    "id": gw_id,
                    "label": f"Passerelle\n{gateway}",
                    "kind": "gateway",
                    "details": details,
                }
            }
        )
        target = f"if:{dev}" if dev and any(n["data"]["id"] == f"if:{dev}" for n in nodes) else "host"
        edges.append(
            {"data": {"id": f"default-{index}", "source": target, "target": gw_id, "label": "route par défaut"}}
        )

    return {"nodes": nodes, "edges": edges}
