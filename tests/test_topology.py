from toponux.analyzers.topology import build_graph


def test_graph_is_simplified_and_keeps_only_default_gateway():
    snapshot = {
        "interfaces": [
            {"ifname": "lo", "operstate": "UNKNOWN", "addr_info": [{"local": "127.0.0.1", "prefixlen": 8}]},
            {"ifname": "eth0", "operstate": "UP", "mtu": 1500, "addr_info": [{"local": "192.0.2.10", "prefixlen": 24}]},
            {"ifname": "docker0", "operstate": "UP", "addr_info": [{"local": "172.17.0.1", "prefixlen": 16}]},
            {"ifname": "veth123", "operstate": "UP", "master": "docker0", "addr_info": []},
        ],
        "routes": {"ipv4": [
            {"dst": "default", "gateway": "192.0.2.1", "dev": "eth0", "table": "main"},
            {"dst": "192.0.2.0/24", "dev": "eth0", "table": "main"},
            {"type": "local", "dst": "127.0.0.1", "dev": "lo", "table": "local"},
        ], "ipv6": []},
    }
    graph = build_graph(snapshot)
    ids = {node["data"]["id"] for node in graph["nodes"]}
    kinds = {node["data"]["kind"] for node in graph["nodes"]}
    assert "host" in ids
    assert "if:eth0" in ids
    assert "bridge:docker0" in ids
    assert "if:lo" not in ids
    assert not any("veth" in node_id for node_id in ids)
    assert not any(node_id.startswith("route:") for node_id in ids)
    assert "gateway:ipv4:192.0.2.1:0" in ids
    assert kinds == {"host", "interface", "bridge", "gateway"}


def test_graph_without_interfaces_or_routes_still_has_host():
    graph = build_graph({"interfaces": [], "routes": {"ipv4": [], "ipv6": []}})
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["data"]["id"] == "host"
    assert graph["edges"] == []
