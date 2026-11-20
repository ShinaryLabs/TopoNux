import pytest
from fastapi.testclient import TestClient

import toponux.api.routes as routes
from toponux.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    routes._hits.clear()
    yield
    routes._hits.clear()


def _fake_ping(target, count=4):
    return {"ok": True, "target": target, "count": count, "output": "fake ping"}


def test_ping_endpoint_returns_probe_result(monkeypatch):
    monkeypatch.setattr(routes, "run_ping", _fake_ping)

    response = client.post("/api/tools/ping", json={"target": "192.0.2.10", "count": 1})

    assert response.status_code == 200
    assert response.json()["target"] == "192.0.2.10"


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
