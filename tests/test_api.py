import pytest
from fastapi.testclient import TestClient

import toponux.api.routes as routes
from toponux.main import app

client = TestClient(app, base_url="http://127.0.0.1:8765")


@pytest.fixture(autouse=True)
def reset_rate_limits():
    routes._hits.clear()
    routes._scan_hits.clear()
    yield
    routes._hits.clear()
    routes._scan_hits.clear()


def _fake_ping(target, count=4):
    return {"ok": True, "target": target, "count": count, "output": "fake ping"}


def test_ping_endpoint_returns_probe_result(monkeypatch):
    monkeypatch.setattr(routes, "run_ping", _fake_ping)

    response = client.post("/api/tools/ping", json={"target": "192.0.2.10", "count": 1})

    assert response.status_code == 200
    assert response.json()["target"] == "192.0.2.10"


def test_scan_endpoint_returns_scan_summary(monkeypatch):
    monkeypatch.setattr(routes, "collect_interfaces", lambda: [{"ifname": "eth0"}])
    monkeypatch.setattr(
        routes,
        "scan_local_subnets",
        lambda interfaces: {
            "available": True,
            "networks": [{"interface": "eth0", "network": "192.0.2.0/24"}],
            "scanned": 254,
            "responsive": 3,
            "truncated": False,
            "message": "Scanned 254 IPv4 host(s); 3 replied.",
        },
    )

    response = client.post("/api/tools/scan")

    assert response.status_code == 200
    assert response.json()["scanned"] == 254
    assert response.json()["responsive"] == 3


def test_scan_endpoint_is_rate_limited(monkeypatch):
    monkeypatch.setattr(routes, "collect_interfaces", lambda: [])
    monkeypatch.setattr(routes, "scan_local_subnets", lambda interfaces: {"available": True, "scanned": 0})

    for _ in range(routes.SCAN_RATE_LIMIT):
        assert client.post("/api/tools/scan").status_code == 200

    blocked = client.post("/api/tools/scan")

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_ipv6_endpoint_describes_address_locally():
    response = client.post("/api/tools/ipv6", json={"target": "fe80::1%eth0"})

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "Link-local unicast"
    assert data["zone"] == "eth0"
    assert data["properties"]["link_local"] is True


def test_ipv6_endpoint_rejects_ipv4():
    response = client.post("/api/tools/ipv6", json={"target": "192.0.2.10"})

    assert response.status_code == 400
    assert "IPv6" in response.json()["detail"]


def test_tools_are_rate_limited(monkeypatch):
    monkeypatch.setattr(routes, "run_ping", _fake_ping)

    for _ in range(routes.TOOL_RATE_LIMIT):
        assert client.post("/api/tools/ping", json={"target": "192.0.2.10"}).status_code == 200

    blocked = client.post("/api/tools/ping", json={"target": "192.0.2.10"})

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


@pytest.mark.parametrize("host", ["127.0.0.1:8765", "localhost:8765", "[::1]:8765", "192.0.2.10"])
def test_local_and_ip_hosts_are_accepted(host):
    assert client.get("/", headers={"host": host}).status_code == 200


def test_foreign_host_is_rejected():
    assert client.get("/", headers={"host": "evil.example"}).status_code == 400


def test_configured_host_is_accepted(monkeypatch):
    monkeypatch.setenv("TOPONUX_ALLOWED_HOSTS", "0.0.0.0,server.example")

    assert client.get("/", headers={"host": "server.example:8765"}).status_code == 200


@pytest.mark.parametrize("origin", ["http://evil.example", "null", "http://127.0.0.1:9999"])
def test_cross_origin_scan_is_refused(monkeypatch, origin):
    monkeypatch.setattr(routes, "collect_interfaces", lambda: pytest.fail("scan must not start"))

    assert client.post("/api/tools/scan", headers={"origin": origin}).status_code == 403


def test_same_origin_post_is_accepted():
    response = client.post("/api/tools/ipv6", json={"target": "::1"}, headers={"origin": "http://127.0.0.1:8765"})

    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/api/docs", "/docs", "/redoc", "/openapi.json"])
def test_api_documentation_is_disabled(path):
    assert client.get(path).status_code == 404


def test_scan_reports_unreadable_interfaces(monkeypatch):
    def broken():
        raise ValueError("invalid JSON")

    monkeypatch.setattr(routes, "collect_interfaces", broken)

    assert client.post("/api/tools/scan").json()["available"] is False


def test_unexpected_firewall_shape_does_not_break_the_snapshot(monkeypatch):
    monkeypatch.setattr(routes, "COLLECTORS", {"firewall": lambda: ["unexpected"]})

    response = client.get("/api/snapshot")

    assert response.status_code == 200
    assert response.json()["firewall_view"]["available"] is False
    assert "firewall_view" in response.json()["errors"]
