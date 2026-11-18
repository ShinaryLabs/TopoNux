from fastapi import APIRouter
from toponux.collectors.interfaces import collect_interfaces
from toponux.collectors.routes import collect_routes
from toponux.collectors.rules import collect_policy_rules
from toponux.collectors.firewall import collect_firewall
from toponux.models.network import collect_snapshot
from toponux.analyzers.topology import build_graph

router = APIRouter()

COLLECTORS = {
    "interfaces": collect_interfaces,
    "routes": collect_routes,
    "policy_rules": collect_policy_rules,
    "firewall": collect_firewall,
}

@router.get("/api/snapshot")
def get_snapshot():
    return collect_snapshot(COLLECTORS)

@router.get("/api/graph")
def get_graph():
    snapshot = collect_snapshot(COLLECTORS)
    return {"snapshot": snapshot, "graph": build_graph(snapshot)}

# Diagnostic tools: bounded, explicit probes only. They never alter network configuration.
from fastapi import HTTPException
from pydantic import BaseModel, Field
from toponux.collectors.diagnostics import run_ping, run_trace, test_tcp_port

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
def api_ping(request: PingRequest):
    try:
        return run_ping(request.target, request.count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/api/tools/trace")
def api_trace(request: TraceRequest):
    try:
        return run_trace(request.target, request.max_hops)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/api/tools/port")
def api_port(request: PortRequest):
    try:
        return test_tcp_port(request.target, request.port, request.timeout)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
