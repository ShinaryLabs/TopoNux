from __future__ import annotations

import re

from toponux.collectors.common import run_text

_PROCESS_RE = re.compile(r'\("([^"]+)",pid=(\d+)')


def _parse_processes(value: str) -> list[dict]:
    processes: dict[tuple[str, int], dict] = {}
    for name, pid in _PROCESS_RE.findall(value):
        process = {"name": name, "pid": int(pid)}
        processes[(name, int(pid))] = process
    return list(processes.values())


def _parse_line(line: str) -> dict | None:
    fields = line.split(maxsplit=6)
    if len(fields) < 6:
        return None
    netid, state, _recv_q, _send_q, local, peer = fields[:6]
    return {
        "netid": netid,
        "state": state,
        "local": local,
        "peer": peer,
        "processes": _parse_processes(fields[6] if len(fields) > 6 else ""),
    }


def collect_sockets() -> list[dict]:
    """Read TCP and UDP sockets through ``ss`` in numeric mode.

    Read-only: ``ss`` inspects the current network namespace. Process names
    are included when the kernel exposes them, which may require privileges
    for sockets owned by other users.
    """
    output = run_text(["ss", "-H", "-t", "-u", "-a", "-n", "-p"])
    records: list[dict] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        record = _parse_line(line)
        if record is not None:
            records.append(record)
    return records
