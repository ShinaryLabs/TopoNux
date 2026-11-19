import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from toponux.analyzers.firewall import normalize_firewall
from toponux.analyzers.topology import build_graph
from toponux.collectors.diagnostics import run_ping, run_trace, test_tcp_port
from toponux.collectors.firewall import collect_firewall
from toponux.collectors.interfaces import collect_interfaces
from toponux.collectors.neighbors import collect_neighbors
from toponux.collectors.routes import collect_routes
from toponux.collectors.rules import collect_policy_rules
from toponux.models.network import collect_snapshot

router = APIRouter()

COLLECTORS = {
    "interfaces": collect_interfaces,
    "neighbors": collect_neighbors,
    "routes": collect_routes,
    "policy_rules": collect_policy_rules,
    "firewall": collect_firewall,
}

# Active probes cost packets and time: cap them per client.
TOOL_RATE_LIMIT = 10
TOOL_RATE_WINDOW = 60.0

_hits: dict[str, deque[float]] = defaultdict(deque)
_hits_lock = threading.Lock()


def _check_rate_limit(client: str) -> None:
    """Allow a bounded number of diagnostic probes per client and per minute."""
    now = time.monotonic()
    with _hits_lock:
        hits = _hits[client]
        while hits and now - hits[0] > TOOL_RATE_WINDOW:
            hits.popleft()
        if len(hits) >= TOOL_RATE_LIMIT:
            retry_after = max(1, int(TOOL_RATE_WINDOW - (now - hits[0])))
            raise HTTPException(
                status_code=429,
                detail="Too many network probes. Try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)


def _client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _with_firewall_view(snapshot: dict) -> dict:
    snapshot["firewall_view"] = normalize_firewall(snapshot.get("firewall"))
    return snapshot


@router.get("/api/snapshot")
def get_snapshot():
    return _with_firewall_view(collect_snapshot(COLLECTORS))


@router.get("/api/graph")
def get_graph():
    snapshot = _with_firewall_view(collect_snapshot(COLLECTORS))
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
