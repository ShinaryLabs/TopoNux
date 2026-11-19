from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

TIMEOUT_SECONDS = 10


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a read-only system command and reject missing binaries or failures."""
    if shutil.which(command[0]) is None:
        raise RuntimeError(f"Command not found: {command[0]}")
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=TIMEOUT_SECONDS)
    if result.returncode != 0:
        message = result.stderr.strip() or f"return code {result.returncode}"
        raise RuntimeError(f"{' '.join(command)} : {message}")
    return result


def run_json(command: list[str]) -> Any:
    """Run a read-only system command and decode its JSON output.

    Commands that print nothing yield an empty list, and a JSON ``null`` is
    normalized to an empty list too, so callers never propagate ``None``.
    """
    payload = _run(command).stdout.strip()
    value = json.loads(payload) if payload else []
    return [] if value is None else value


def run_text(command: list[str]) -> str:
    return _run(command).stdout
