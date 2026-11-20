from __future__ import annotations

from .common import run_json

_COMMANDS = {
    "links": ["ip", "-j", "-d", "link", "show"],
    "bridge_links": ["bridge", "-j", "link", "show"],
    "bridge_vlans": ["bridge", "-j", "vlan", "show"],
}


def collect_l2() -> dict:
    """Collect layer-2 structure: link details, bridge ports and bridge VLANs.

    Each command is independent. A missing ``bridge`` binary or a permission
    error is reported under ``errors`` without hiding the other results.
    """
    result: dict = {}
    errors: dict[str, str] = {}
    for key, command in _COMMANDS.items():
        try:
            result[key] = run_json(command)
        except Exception as exc:  # reported to the UI; collection stays read-only
            result[key] = []
            errors[key] = str(exc)
    if errors:
        result["errors"] = errors
    return result
