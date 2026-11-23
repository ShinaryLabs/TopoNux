import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from toponux.analyzers.firewall import normalize_firewall
from toponux.analyzers.neighbors import normalize_neighbors
from toponux.analyzers.sockets import normalize_sockets
from toponux.analyzers.topology import build_graph
from toponux.collectors.diagnostics import (
    inspect_ipv6,
    run_ping,
    run_trace,
    scan_local_subnets,
    test_tcp_port,
)
from toponux.collectors.firewall import collect_firewall
from toponux.collectors.interfaces import collect_interfaces
from toponux.collectors.l2 import collect_l2
from toponux.collectors.neighbors import collect_neighbors
from toponux.collectors.routes import collect_routes
from toponux.collectors.rules import collect_policy_rules
from toponux.collectors.sockets import collect_sockets
from toponux.models.network import collect_snapshot

router = APIRouter()

COLLECTORS = {
    "interfaces": collect_interfaces,
    "l2": collect_l2,
    "neighbors": collect_neighbors,
    "routes": collect_routes,
    "policy_rules": collect_policy_rules,
    "sockets": collect_sockets,
    "firewall": collect_firewall,
}

# Active probes cost packets and time: cap them per client.
TOOL_RATE_LIMIT = 10
TOOL_RATE_WINDOW = 60.0
SCAN_RATE_LIMIT = 2
SCAN_RATE_WINDOW = 60.0

_hits: dict[str, deque[float]] = defaultdict(deque)
_scan_hits: dict[str, deque[float]] = defaultdict(deque)
_hits_lock = threading.Lock()


def _rate_limit(client: str, hits: dict[str, deque[float]], limit: int, window: float, detail: str) -> None:
    now = time.monotonic()
    with _hits_lock:
        client_hits = hits[client]
        while client_hits and now - client_hits[0] > window:
            client_hits.popleft()
        if len(client_hits) >= limit:
            retry_after = max(1, int(window - (now - client_hits[0])))
            raise HTTPException(
                status_code=429,
                detail=detail,
                headers={"Retry-After": str(retry_after)},
            )
        client_hits.append(now)


def _check_rate_limit(client: str) -> None:
    """Allow a bounded number of diagnostic probes per client and per minute."""
    _rate_limit(client, _hits, TOOL_RATE_LIMIT, TOOL_RATE_WINDOW, "Too many network probes. Try again shortly.")


def _check_scan_rate_limit(client: str) -> None:
    """A scan sends many packets, so it gets a stricter budget than one probe."""
    _rate_limit(client, _scan_hits, SCAN_RATE_LIMIT, SCAN_RATE_WINDOW, "Too many subnet scans. Try again shortly.")


def _client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enrich_snapshot(snapshot: dict) -> dict:
    snapshot["firewall_view"] = normalize_firewall(snapshot.get("firewall"))
    snapshot["neighbors_view"] = normalize_neighbors(snapshot.get("neighbors"))
    snapshot["sockets_view"] = normalize_sockets(
        snapshot.get("sockets"),
        snapshot.get("interfaces"),
        snapshot.get("errors", {}).get("sockets"),
    )
    return snapshot


@router.get("/api/snapshot")
def get_snapshot():
    return _enrich_snapshot(collect_snapshot(COLLECTORS))


@router.get("/api/graph")
def get_graph():
    snapshot = _enrich_snapshot(collect_snapshot(COLLECTORS))
    return {"snapshot": snapshot, "graph": build_graph(snapshot)}


# Diagnostic tools: bounded, explicit probes only. They never alter network configuration.
class TargetRequest(BaseModel):
    target: str = Field(min_length=1, max_length=253)


class PingRequest(TargetRequest):
    count: int = Field(default=4, ge=1, le=10)


class TraceRequest(TargetRequest):
    max_hops: int = Field(default=20, ge=1, le=30)


class PortRequest(TargetRequest):
    port: int = Field(ge=1, le=65535)
    timeout: float = Field(default=2.0, ge=0.5, le=5.0)


@router.post("/api/tools/ping")
def api_ping(payload: PingRequest, request: Request):
    _check_rate_limit(_client_id(request))
    try:
        return run_ping(payload.target, payload.count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/tools/scan")
def api_scan(request: Request):
    """Ping every IPv4 host of the local subnets to refresh the neighbour cache."""
    _check_scan_rate_limit(_client_id(request))
    try:
        interfaces = collect_interfaces()
    except RuntimeError:
        return {
            "available": False,
            "error": "Interface information is unavailable.",
            "networks": [],
            "scanned": 0,
            "responsive": 0,
            "truncated": False,
        }
    return scan_local_subnets(interfaces)


@router.post("/api/tools/trace")
def api_trace(payload: TraceRequest, request: Request):
    _check_rate_limit(_client_id(request))
    try:
        return run_trace(payload.target, payload.max_hops)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/tools/port")
def api_port(payload: PortRequest, request: Request):
    _check_rate_limit(_client_id(request))
    try:
        return test_tcp_port(payload.target, payload.port, payload.timeout)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/tools/ipv6")
def api_ipv6(payload: TargetRequest):
    """Describe an IPv6 address from local computation only. No packet is sent."""
    try:
        return inspect_ipv6(payload.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
