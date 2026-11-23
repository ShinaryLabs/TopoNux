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


def _link_info(record: dict) -> dict:
    return record.get("linkinfo") or {}


def _link_kind(record: dict) -> str:
    info_kind = _link_info(record).get("info_kind", "")
    if info_kind == "bridge" or _is_virtual_bridge(record):
        return "bridge"
    if info_kind == "bond":
        return "bond"
    if info_kind == "vlan":
        return "vlan"
    return "interface"


def _node_id(name: str, kind: str) -> str:
    prefix = {"bridge": "bridge", "bond": "bond", "vlan": "vlan"}.get(kind, "if")
    return f"{prefix}:{name}"


def _vlan_by_interface(snapshot: dict) -> dict[str, list[dict]]:
    l2 = snapshot.get("l2")
    entries = l2.get("bridge_vlans", []) if isinstance(l2, dict) else []
    result: dict[str, list[dict]] = {}
    for entry in entries if isinstance(entries, list) else []:
        name = entry.get("ifname")
        if name:
            result[name] = entry.get("vlans", [])
    return result


def _bridge_port_by_interface(snapshot: dict) -> dict[str, dict]:
    l2 = snapshot.get("l2")
    entries = l2.get("bridge_links", []) if isinstance(l2, dict) else []
    return {entry["ifname"]: entry for entry in entries if isinstance(entry, dict) and entry.get("ifname")}


def _vlans_text(vlans: list[dict]) -> str:
    parts = []
    for vlan in vlans:
        flags = ", ".join(str(flag) for flag in vlan.get("flags", []))
        suffix = f" ({flags})" if flags else ""
        parts.append(f"{vlan.get('vlan', '?')}{suffix}")
    return ", ".join(parts)


def _l2_summary(record: dict) -> str | None:
    """Short layer-2 description used in labels and the interfaces table."""
    info = _link_info(record)
    data = info.get("info_data") or {}
    kind = info.get("info_kind")
    if kind == "vlan":
        parent = data.get("link", "?")
        return f"vlan {data.get('id', '?')} on {parent}"
    if kind == "bond":
        mode = data.get("mode", "?")
        return f"bond {mode}"
    if kind == "bridge":
        return "bridge"
    return None


def _l2_details(record: dict, vlans: list[dict], port: dict | None) -> list[str]:
    info = _link_info(record)
    data = info.get("info_data") or {}
    kind = info.get("info_kind")
    lines: list[str] = []
    if kind == "vlan":
        lines.append(f"VLAN: {data.get('id', '?')} on {data.get('link', '?')}")
        if data.get("protocol"):
            lines.append(f"VLAN protocol: {data['protocol']}")
    elif kind == "bond":
        lines.append(f"Bond mode: {data.get('mode', '?')}")
        if data.get("miimon") is not None:
            lines.append(f"Bond miimon: {data['miimon']} ms")
        if data.get("xmit_hash_policy"):
            lines.append(f"Bond hash policy: {data['xmit_hash_policy']}")
        if data.get("lacp_rate"):
            lines.append(f"Bond LACP rate: {data['lacp_rate']}")
    elif kind == "bridge":
        lines.append(f"STP: {'enabled' if data.get('stp_state') else 'disabled'}")
        lines.append(f"VLAN filtering: {'enabled' if data.get('vlan_filtering') else 'disabled'}")
    if vlans:
        lines.append(f"Bridge VLANs: {_vlans_text(vlans)}")
    if port:
        if port.get("state"):
            lines.append(f"Bridge port state: {port['state']}")
        if port.get("port_no") is not None:
            lines.append(f"Bridge port number: {port['port_no']}")
    return lines


def _merged_records(snapshot: dict) -> dict[str, dict]:
    """Merge address data (interfaces) with detailed link data (ip -d link)."""
    l2 = snapshot.get("l2")
    l2_links = l2.get("links", []) if isinstance(l2, dict) else []
    links = {link["ifname"]: link for link in l2_links if isinstance(link, dict) and link.get("ifname")}
    records: dict[str, dict] = {}
    for iface in snapshot.get("interfaces", []):
        name = iface.get("ifname")
        if not name:
            continue
        records[name] = {**links.get(name, {}), **iface}
    for name, link in links.items():
        records.setdefault(name, dict(link))
    return records


def build_graph(snapshot: dict) -> dict:
    """Build a simplified overview; full data stays in detail tabs.

    Layer-2 links (bridges, bonds, VLAN devices) are only expanded when the
    ``l2`` collector is present, so snapshots without it keep the old view.
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    records = _merged_records(snapshot)
    vlans_by_interface = _vlan_by_interface(snapshot)
    bridge_ports = _bridge_port_by_interface(snapshot)
    node_id_by_name: dict[str, str] = {}

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

    def should_show(record: dict) -> bool:
        name = record.get("ifname", "unknown")
        if name == "lo" or _is_veth(record):
            return False
        kind = _link_kind(record)
        if _is_virtual_bridge(record):
            return record.get("operstate") != "DOWN"
        if kind in {"bridge", "bond", "vlan"}:
            return True
        if _addresses(record):
            return True
        master = record.get("master")
        return bool(master and master in records and not _is_virtual_bridge(records[master]))

    for name, record in records.items():
        if not should_show(record):
            continue
        kind = _link_kind(record)
        node_id = _node_id(name, kind)
        node_id_by_name[name] = node_id
        addresses = _addresses(record)
        networks = _network_labels(record)
        state = record.get("operstate", "UNKNOWN")
        summary = _l2_summary(record)
        vlans = vlans_by_interface.get(name, [])
        port = bridge_ports.get(name)
        details = [f"Interface: {name}", f"State: {state}", f"MTU: {record.get('mtu', '?')}"]
        details.append(f"MAC: {record.get('address', '—')}")
        if kind != "interface":
            details.append(f"Layer 2 type: {kind}")
        if summary:
            details.append(f"Layer 2: {summary}")
        if record.get("master"):
            details.append(f"Master: {record['master']}")
        details.extend(_l2_details(record, vlans, port))
        details.append("Addresses:")
        details.extend(addresses or ["None"])

        if kind == "bridge":
            members = [other for other in records.values() if other.get("master") == name]
            details.insert(4, f"Member interfaces: {len(members)}")
            label_subject = ", ".join(networks) if networks else "bridge"
        elif kind == "bond":
            members = [other for other in records.values() if other.get("master") == name]
            details.insert(4, f"Slave interfaces: {len(members)}")
            label_subject = summary or "bond"
        elif kind == "vlan":
            label_subject = summary or "vlan"
        else:
            label_subject = addresses[0] if addresses else state

        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "label": f"{name}\n{label_subject}",
                    "kind": kind,
                    "name": name,
                    "state": state,
                    "details": "\n".join(details),
                }
            }
        )

    # Attach members to their bridge, bond or VLAN parent; top-level links go to the host.
    for name, node_id in node_id_by_name.items():
        record = records[name]
        kind = _link_kind(record)
        info_data = _link_info(record).get("info_data") or {}
        parent_name = info_data.get("link") if kind == "vlan" else record.get("master")
        parent_id = node_id_by_name.get(parent_name) if parent_name else None
        if parent_id and parent_id != node_id:
            parent_record = records.get(str(parent_name))
            parent_kind = _link_kind(parent_record) if parent_record else "interface"
            if kind == "vlan":
                edge_label = f"vlan {info_data.get('id', '?')}"
            elif parent_kind == "bond":
                edge_label = "slave"
            elif parent_kind == "bridge":
                edge_label = "port"
            else:
                edge_label = "member"
        else:
            parent_id = "host"
            if _is_virtual_bridge(record):
                edge_label = "virtual network"
            elif kind == "bridge":
                edge_label = "bridge"
            elif kind == "bond":
                edge_label = "bond"
            elif kind == "vlan":
                edge_label = "vlan"
            else:
                edge_label = "interface"
        edges.append({"data": {"id": f"l2-{name}", "source": parent_id, "target": node_id, "label": edge_label}})

    # Default routes are resolved after neighbours so a gateway that is already
    # present in the ARP/NDP cache reuses the same node instead of being duplicated.
    default_routes = [
        (family, route)
        for family, routes in snapshot.get("routes", {}).items()
        for route in routes
        if route.get("dst") == "default"
    ]
    gateway_hops = {(route.get("dev"), route.get("gateway")) for _, route in default_routes if route.get("gateway")}

    # ARP/NDP neighbours are shown as small leaf nodes attached to the interface
    # or bridge that reaches them. Docker networks stay flagged for the UI filter.
    grouped: dict[tuple[str, str], dict] = {}
    neighbor_node_by_address: dict[tuple[str, str], dict] = {}
    raw_neighbors = snapshot.get("neighbors", [])
    for entry in raw_neighbors if isinstance(raw_neighbors, list) else []:
        dev, mac, dst = entry.get("dev"), entry.get("lladdr"), entry.get("dst")
        if not dev or not mac or not dst or dev == "lo" or _VETH_RE.fullmatch(dev):
            continue
        parent = node_id_by_name.get(dev)
        if parent is None:
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
        node = {
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
        nodes.append(node)
        for address in addresses:
            neighbor_node_by_address[(dev, address)] = node["data"]
        # A neighbour that is also a default gateway is drawn once, by the
        # default-route edge below, instead of twice with parallel edges.
        if any((dev, address) in gateway_hops for address in addresses):
            continue
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
    linked_defaults: set[tuple[str, str]] = set()
    for index, (family, route) in enumerate(default_routes):
        gateway = route.get("gateway")
        dev = route.get("dev")
        hop = gateway or dev or "unknown"
        route_details = [
            f"Family: {family}",
            f"Interface: {dev or '—'}",
            f"Table: {route.get('table', 'main')}",
            f"Metric: {route.get('metric', '—')}",
        ]
        neighbor = neighbor_node_by_address.get((dev, gateway)) if gateway and dev else None
        if neighbor is None:
            gw_id = f"gateway:{family}:{hop}:{index}"
            label = f"Gateway\n{gateway}" if gateway else f"Default route\n{dev or '—'}"
            gateway_details = "\n".join(
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
                        "details": gateway_details,
                    }
                }
            )
        else:
            # Merge the gateway role into the existing neighbour node.
            gw_id = neighbor["id"]
            neighbor["kind"] = "gateway"
            neighbor["label"] = f"Gateway\n{gateway}"
            neighbor["details"] = "\n".join(
                [neighbor["details"], "Default route:", *(f"  {line}" for line in route_details)]
            )
        target = node_id_by_name.get(dev or "", "host")
        if (target, gw_id) in linked_defaults:
            continue
        linked_defaults.add((target, gw_id))
        edges.append({"data": {"id": f"default-{index}", "source": target, "target": gw_id, "label": "default route"}})

    return {"nodes": nodes, "edges": edges}
