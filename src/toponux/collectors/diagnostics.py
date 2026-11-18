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
        raise ValueError("Cible invalide.")
    try:
        ipaddress.ip_address(target)
        return target
    except ValueError as exc:
        if not _HOST_RE.fullmatch(target):
            raise ValueError("Indique une adresse IP ou un nom DNS valide.") from exc
        return target


def _run(command: list[str], timeout: int = 35) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Le diagnostic a dépassé le délai maximal.") from exc


def route_lookup(target: str) -> dict:
    """Read the kernel's selected route for a destination."""
    binary = shutil.which("ip")
    if not binary:
        return {"available": False, "output": "Commande ip introuvable."}
    result = _run([binary, "route", "get", target], timeout=3)
    return {
        "available": result.returncode == 0,
        "output": (result.stdout + result.stderr).strip() or "Aucune route retournée.",
    }


def run_ping(target: str, count: int = 4) -> dict:
    target = validate_target(target)
    binary = shutil.which("ping")
    if not binary:
        return {"ok": False, "error": "La commande ping n'est pas installée."}
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
            "error": "Aucun outil disponible. Installe tracepath (iputils-tracepath) ou traceroute.",
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
                "interpretation": (
                    "Connexion TCP établie. Le chemin réseau et les règles rencontrées l'ont laissée passer."
                ),
            }
    except ConnectionRefusedError:
        result, explanation = (
            "refused",
            "La cible a répondu par un refus TCP (RST). Le port peut être fermé "
            "ou un équipement peut rejeter la connexion.",
        )
    except TimeoutError:
        result, explanation = (
            "timeout",
            "Aucune réponse dans le délai imparti. Filtrage, perte réseau ou hôte silencieux sont possibles.",
        )
    except OSError as exc:
        result, explanation = "unreachable", f"Échec réseau : {exc}"
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
