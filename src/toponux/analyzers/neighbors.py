from __future__ import annotations

import re
from pathlib import Path

from toponux.analyzers.topology import _VETH_RE, _is_docker_interface

_OUI_PATHS = (
    Path("/usr/share/ieee-data/oui.txt"),
    Path("/var/lib/ieee-data/oui.txt"),
    Path("/usr/share/misc/oui.txt"),
    Path("/usr/share/hwdata/oui.txt"),
    Path("/usr/share/nmap/nmap-mac-prefixes"),
)

_oui_cache: dict[str, str] | None = None


def _load_oui() -> dict[str, str]:
    global _oui_cache
    if _oui_cache is not None:
        return _oui_cache
    mapping: dict[str, str] = {}
    for path in _OUI_PATHS:
        if not path.is_file():
            continue
        try:
            with path.open(encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    match = re.match(
                        r"^\s*([0-9A-Fa-f]{2})[-:]?([0-9A-Fa-f]{2})[-:]?([0-9A-Fa-f]{2})\s*\(hex\)\s*(.+?)\s*$",
                        line,
                    )
                    if match:
                        prefix = (match.group(1) + match.group(2) + match.group(3)).upper()
                        mapping.setdefault(prefix, match.group(4).strip())
                        continue
                    match = re.match(r"^([0-9A-Fa-f]{6})\s+(.+?)\s*$", line)
                    if match and not line.lstrip().startswith("#"):
                        mapping.setdefault(match.group(1).upper(), match.group(2).strip())
        except OSError:
            continue
        if mapping:
            break
    _oui_cache = mapping
    return _oui_cache


def lookup_vendor(mac: str) -> str | None:
    """Return the OUI vendor for *mac*, or None when no database matches."""
    prefix = mac.replace(":", "").replace("-", "").replace(".", "").upper()[:6]
    if len(prefix) != 6 or not all(character in "0123456789ABCDEF" for character in prefix):
        return None
    try:
        first_byte = int(prefix[:2], 16)
    except ValueError:
        return None
    if first_byte & 0x02:
        return "Locally administered"
    return _load_oui().get(prefix)


def normalize_neighbors(entries: list[dict] | None) -> list[dict]:
    """Group ARP/NDP entries by (interface, MAC) and add OUI vendor information."""
    grouped: dict[tuple[str, str], dict] = {}
    for entry in entries or []:
        dev = entry.get("dev")
        mac = entry.get("lladdr")
        dst = entry.get("dst")
        if not dev or not mac or not dst or dev == "lo" or _VETH_RE.fullmatch(dev):
            continue
        state = entry.get("state", "")
        if isinstance(state, list):
            state = " ".join(str(item) for item in state) or "UNKNOWN"
        else:
            state = str(state) or "UNKNOWN"
        record = grouped.setdefault(
            (dev, mac),
            {
                "interface": dev,
                "mac": mac,
                "addresses": [],
                "ipv4": [],
                "ipv6": [],
                "states": [],
                "docker": _is_docker_interface(dev),
            },
        )
        if dst not in record["addresses"]:
            record["addresses"].append(dst)
        family = "ipv6" if ":" in dst else "ipv4"
        if dst not in record[family]:
            record[family].append(dst)
        if state not in record["states"]:
            record["states"].append(state)

    result = []
    for record in grouped.values():
        mac = record["mac"]
        vendor = lookup_vendor(mac) or "Unknown"
        result.append(
            {
                "interface": record["interface"],
                "mac": mac,
                "oui": mac[:8].upper(),
                "addresses": record["addresses"],
                "ipv4": record["ipv4"],
                "ipv6": record["ipv6"],
                "state": ", ".join(record["states"]),
                "docker": record["docker"],
                "vendor": vendor,
            }
        )
    result.sort(key=lambda item: (item["interface"], item["mac"]))
    return result
