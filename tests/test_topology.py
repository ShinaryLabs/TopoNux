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
