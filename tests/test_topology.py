from toponux.analyzers.topology import build_graph


def test_graph_is_simplified_and_keeps_only_default_gateway():
    snapshot = {
        "interfaces": [
            {"ifname": "lo", "operstate": "UNKNOWN", "addr_info": [{"local": "127.0.0.1", "prefixlen": 8}]},
            {"ifname": "eth0", "operstate": "UP", "mtu": 1500, "addr_info": [{"local": "192.0.2.10", "prefixlen": 24}]},
            {"ifname": "docker0", "operstate": "UP", "addr_info": [{"local": "172.17.0.1", "prefixlen": 16}]},
            {"ifname": "veth123", "operstate": "UP", "master": "docker0", "addr_info": []},
        ],
        "routes": {
            "ipv4": [
                {"dst": "default", "gateway": "192.0.2.1", "dev": "eth0", "table": "main"},
                {"dst": "192.0.2.0/24", "dev": "eth0", "table": "main"},
                {"type": "local", "dst": "127.0.0.1", "dev": "lo", "table": "local"},
            ],
            "ipv6": [],
        },
    }
    graph = build_graph(snapshot)
    ids = {node["data"]["id"] for node in graph["nodes"]}
    kinds = {node["data"]["kind"] for node in graph["nodes"]}
    assert ids == {"host", "if:eth0", "bridge:docker0", "gateway:ipv4:192.0.2.1:0"}
    assert kinds == {"host", "interface", "bridge", "gateway"}


def test_graph_without_interfaces_or_routes_still_has_host():
    graph = build_graph({"interfaces": [], "routes": {"ipv4": [], "ipv6": []}})
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["data"]["id"] == "host"
    assert graph["edges"] == []


def test_user_bridge_is_not_treated_as_container_network():
    snapshot = {
        "interfaces": [
            {"ifname": "br-wan", "operstate": "UP", "addr_info": [{"local": "198.51.100.1", "prefixlen": 24}]},
            {"ifname": "br-0123456789ab", "operstate": "UP", "addr_info": [{"local": "172.18.0.1", "prefixlen": 16}]},
        ],
        "routes": {},
    }

    ids = {node["data"]["id"] for node in build_graph(snapshot)["nodes"]}

    assert "if:br-wan" in ids
    assert "bridge:br-0123456789ab" in ids


def test_on_link_default_route_is_shown_without_gateway():
    snapshot = {
        "interfaces": [],
        "routes": {"ipv4": [{"dst": "default", "dev": "ppp0", "table": "main"}]},
    }

    graph = build_graph(snapshot)
    nodes = {node["data"]["id"]: node["data"] for node in graph["nodes"]}

    assert "gateway:ipv4:ppp0:0" in nodes
    assert "Default route" in nodes["gateway:ipv4:ppp0:0"]["label"]
    assert "on-link" in nodes["gateway:ipv4:ppp0:0"]["details"]


def test_neighbors_attach_to_their_interface_and_flag_docker_networks():
    snapshot = {
        "interfaces": [
            {"ifname": "eth1", "operstate": "UP", "addr_info": [{"local": "203.0.113.10", "prefixlen": 24}]},
            {"ifname": "docker0", "operstate": "UP", "addr_info": [{"local": "172.17.0.1", "prefixlen": 16}]},
        ],
        "neighbors": [
            {"dst": "203.0.113.1", "dev": "eth1", "lladdr": "00:00:5e:00:53:01", "state": ["REACHABLE"]},
            {"dst": "172.17.0.2", "dev": "docker0", "lladdr": "00:00:5e:00:53:02", "state": ["STALE"]},
        ],
        "routes": {},
    }

    graph = build_graph(snapshot)
    nodes = {node["data"]["id"]: node["data"] for node in graph["nodes"]}
    edges = {edge["data"]["id"]: edge["data"] for edge in graph["edges"]}

    lan = nodes["neighbor:eth1:00:00:5e:00:53:01"]
    assert lan["kind"] == "neighbor"
    assert lan["family"] == "ip"
    assert lan["docker"] is False
    assert lan["label"] == "203.0.113.1"
    assert edges["neighbor-eth1-00:00:5e:00:53:01"]["source"] == "if:eth1"

    container = nodes["neighbor:docker0:00:00:5e:00:53:02"]
    assert container["docker"] is True
    assert edges["neighbor-docker0-00:00:5e:00:53:02"]["source"] == "bridge:docker0"


def test_neighbor_addresses_are_grouped_per_mac_and_family_is_detected():
    snapshot = {
        "interfaces": [
            {"ifname": "eth0", "operstate": "UP", "addr_info": [{"local": "192.0.2.10", "prefixlen": 24}]},
        ],
        "neighbors": [
            {"dst": "192.0.2.20", "dev": "eth0", "lladdr": "aa:bb:cc:dd:ee:ff", "state": ["REACHABLE"]},
            {"dst": "fe80::1", "dev": "eth0", "lladdr": "aa:bb:cc:dd:ee:ff", "state": ["STALE"]},
            {"dst": "fe80::2", "dev": "eth0", "lladdr": "11:22:33:44:55:66", "state": ["DELAY"]},
        ],
        "routes": {},
    }

    nodes = {node["data"]["id"]: node["data"] for node in build_graph(snapshot)["nodes"]}

    dual = nodes["neighbor:eth0:aa:bb:cc:dd:ee:ff"]
    assert dual["addresses"] == ["192.0.2.20", "fe80::1"]
    assert dual["family"] == "ip"
    assert dual["label"] == "192.0.2.20 (+1)"

    ipv6_only = nodes["neighbor:eth0:11:22:33:44:55:66"]
    assert ipv6_only["family"] == "ip6"


def test_default_gateway_reuses_matching_neighbor_node():
    snapshot = {
        "interfaces": [
            {"ifname": "eth0", "operstate": "UP", "addr_info": [{"local": "192.0.2.10", "prefixlen": 24}]},
        ],
        "neighbors": [
            {"dst": "192.0.2.1", "dev": "eth0", "lladdr": "aa:bb:cc:dd:ee:01", "state": ["REACHABLE"]},
        ],
        "routes": {
            "ipv4": [
                {"dst": "default", "gateway": "192.0.2.1", "dev": "eth0", "table": "main", "metric": 100},
            ],
            "ipv6": [],
        },
    }

    graph = build_graph(snapshot)
    gateways = [node["data"] for node in graph["nodes"] if node["data"]["kind"] == "gateway"]
    edges = {(edge["data"]["source"], edge["data"]["target"], edge["data"]["label"]) for edge in graph["edges"]}

    assert len(gateways) == 1
    gateway = gateways[0]
    assert gateway["id"] == "neighbor:eth0:aa:bb:cc:dd:ee:01"
    assert gateway["label"] == "Gateway\n192.0.2.1"
    assert "Neighbor: 192.0.2.1" in gateway["details"]
    assert "Default route:" in gateway["details"]
    assert "Table: main" in gateway["details"]
    assert ("if:eth0", gateway["id"], "default route") in edges
    assert ("if:eth0", gateway["id"], "neighbor") not in edges


def test_unusable_or_unattached_neighbor_entries_are_skipped():
    snapshot = {
        "interfaces": [
            {"ifname": "eth0", "operstate": "UP", "addr_info": [{"local": "192.0.2.10", "prefixlen": 24}]},
        ],
        "neighbors": [
            {"dst": "192.0.2.30", "dev": "lo", "lladdr": "aa:aa:aa:aa:aa:aa", "state": ["REACHABLE"]},
            {"dst": "192.0.2.31", "dev": "veth123", "lladdr": "bb:bb:bb:bb:bb:bb", "state": ["REACHABLE"]},
            {"dst": "192.0.2.32", "dev": "eth0", "state": ["FAILED"]},
            {"dst": "192.0.2.33", "dev": "eth9", "lladdr": "cc:cc:cc:cc:cc:cc", "state": ["STALE"]},
            {"dst": "192.0.2.34", "dev": "eth0", "lladdr": "dd:dd:dd:dd:dd:dd", "state": ["STALE"]},
        ],
        "routes": {},
    }

    graph = build_graph(snapshot)
    neighbor_ids = [node["data"]["id"] for node in graph["nodes"] if node["data"]["kind"] == "neighbor"]

    assert neighbor_ids == ["neighbor:eth0:dd:dd:dd:dd:dd:dd"]


def test_graph_expands_l2_links_with_vlan_and_bond():
    snapshot = {
        "interfaces": [
            {"ifname": "br0", "operstate": "UP", "addr_info": [{"local": "192.0.2.10", "prefixlen": 24}]},
            {"ifname": "eth0", "operstate": "UP", "master": "br0", "addr_info": []},
            {"ifname": "bond0", "operstate": "UP", "addr_info": [{"local": "10.0.0.1", "prefixlen": 24}]},
            {"ifname": "eth1", "operstate": "UP", "master": "bond0", "addr_info": []},
            {"ifname": "eth1.10", "operstate": "UP", "addr_info": [{"local": "10.0.1.1", "prefixlen": 24}]},
        ],
        "l2": {
            "links": [
                {
                    "ifname": "br0",
                    "linkinfo": {"info_kind": "bridge", "info_data": {"stp_state": 0, "vlan_filtering": 1}},
                },
                {"ifname": "eth0", "master": "br0", "linkinfo": {"info_kind": "bridge_slave"}},
                {"ifname": "bond0", "linkinfo": {"info_kind": "bond", "info_data": {"mode": "802.3ad", "miimon": 100}}},
                {"ifname": "eth1", "master": "bond0", "linkinfo": {"info_kind": "bond_slave"}},
                {
                    "ifname": "eth1.10",
                    "linkinfo": {"info_kind": "vlan", "info_data": {"id": 10, "link": "eth1", "protocol": "802.1Q"}},
                },
            ],
            "bridge_links": [],
            "bridge_vlans": [{"ifname": "br0", "vlans": [{"vlan": 1, "flags": ["PVID", "Egress Untagged"]}]}],
        },
        "routes": {},
    }

    graph = build_graph(snapshot)
    ids = {node["data"]["id"] for node in graph["nodes"]}
    kinds = {node["data"]["kind"] for node in graph["nodes"]}
    edges = {(edge["data"]["source"], edge["data"]["target"], edge["data"]["label"]) for edge in graph["edges"]}

    assert {"host", "bridge:br0", "bond:bond0", "vlan:eth1.10"} <= ids
    assert {"bond", "vlan"} <= kinds
    assert ("bridge:br0", "if:eth0", "port") in edges
    assert ("bond:bond0", "if:eth1", "slave") in edges
    assert ("if:eth1", "vlan:eth1.10", "vlan 10") in edges
