from __future__ import annotations

from pathlib import Path

from .common import run_json

SYS_NET = Path("/sys/class/net")


def _read_stat(ifname: str, metric: str) -> int:
    try:
        return int((SYS_NET / ifname / "statistics" / metric).read_text().strip())
    except (OSError, ValueError):
        return 0


def collect_interfaces() -> list[dict]:
    """Collect network interfaces and enrich them with /sys kernel statistics."""
    interfaces = run_json(["ip", "-j", "address", "show"])
    for iface in interfaces:
        name = iface.get("ifname")
        if not name:
            continue
        iface["stats"] = {
            "rx_bytes": _read_stat(name, "rx_bytes"),
            "tx_bytes": _read_stat(name, "tx_bytes"),
            "rx_errors": _read_stat(name, "rx_errors"),
            "tx_errors": _read_stat(name, "tx_errors"),
            "rx_dropped": _read_stat(name, "rx_dropped"),
            "tx_dropped": _read_stat(name, "tx_dropped"),
        }
    return interfaces
