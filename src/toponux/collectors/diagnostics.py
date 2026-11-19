from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess
import time

_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\.?$"
)


def validate_target(target: str) -> str:
    target = target.strip()
    if not target or target.startswith("-") or any(c.isspace() for c in target):
        raise ValueError("Invalid target.")
    try:
        ipaddress.ip_address(target)
        return target
    except ValueError as exc:
        if not _HOST_RE.fullmatch(target):
            raise ValueError("Provide a valid IP address or DNS name.") from exc
        return target


def _run(command: list[str], timeout: int = 35) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("The diagnostic exceeded its time limit.") from exc


def route_lookup(target: str) -> dict:
    """Read the kernel's selected route for a destination."""
    binary = shutil.which("ip")
    if not binary:
        return {"available": False, "output": "ip command not found."}
    result = _run([binary, "route", "get", target], timeout=3)
    return {
        "available": result.returncode == 0,
        "output": (result.stdout + result.stderr).strip() or "No route returned.",
    }


def run_ping(target: str, count: int = 4) -> dict:
    target = validate_target(target)
    binary = shutil.which("ping")
    if not binary:
        return {"ok": False, "error": "ping is not installed."}
    result = _run([binary, "-n", "-c", str(count), "-W", "2", "--", target], timeout=count * 3 + 3)
    return {
        "ok": result.returncode == 0,
        "target": target,
        "count": count,
        "return_code": result.returncode,
        "reachable": result.returncode == 0,
        "route": route_lookup(target),
        "output": (result.stdout + result.stderr).strip(),
    }


def run_trace(target: str, max_hops: int = 20) -> dict:
    target = validate_target(target)
    tracepath = shutil.which("tracepath")
    traceroute = shutil.which("traceroute")
    if tracepath:
        command, tool = [tracepath, "-n", "-m", str(max_hops), target], "tracepath (UDP)"
    elif traceroute:
        command, tool = [traceroute, "-n", "-m", str(max_hops), "-w", "1", target], "traceroute (UDP)"
    else:
        return {
            "ok": False,
            "target": target,
            "error": "No tool available. Install tracepath (iputils-tracepath) or traceroute.",
        }
    result = _run(command, timeout=max_hops * 2 + 5)
    return {
        "ok": result.returncode == 0,
        "target": target,
        "tool": tool,
        "route": route_lookup(target),
        "return_code": result.returncode,
        "output": (result.stdout + result.stderr).strip(),
    }


def test_tcp_port(target: str, port: int, timeout: float = 2.0) -> dict:
    target = validate_target(target)
    started = time.monotonic()
    try:
        with socket.create_connection((target, port), timeout=timeout) as sock:
            elapsed = round((time.monotonic() - started) * 1000, 2)
            local = sock.getsockname()
            return {
                "target": target,
                "port": port,
                "protocol": "TCP",
                "reachable": True,
                "result": "connected",
                "latency_ms": elapsed,
                "route": route_lookup(target),
                "local_address": f"{local[0]}:{local[1]}",
                "interpretation": ("TCP connection established. The network path and the rules it crossed allowed it."),
            }
    except ConnectionRefusedError:
        result, explanation = (
            "refused",
            "The target answered with a TCP refusal (RST). The port may be closed "
            "or a device may reject the connection.",
        )
    except TimeoutError:
        result, explanation = (
            "timeout",
            "No answer within the time limit. Filtering, packet loss or a silent host are possible.",
        )
    except OSError as exc:
        result, explanation = "unreachable", f"Network failure: {exc}"
    return {
        "target": target,
        "port": port,
        "protocol": "TCP",
        "reachable": False,
        "result": result,
        "latency_ms": round((time.monotonic() - started) * 1000, 2),
        "route": route_lookup(target),
        "interpretation": explanation,
    }
