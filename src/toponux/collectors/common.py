from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


def run_json(command: list[str]) -> Any:
    """Run a read-only system command and decode its JSON output."""
    if shutil.which(command[0]) is None:
        raise RuntimeError(f"Commande introuvable : {command[0]}")
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    if result.returncode != 0:
        message = result.stderr.strip() or f"code de retour {result.returncode}"
        raise RuntimeError(f"{' '.join(command)} : {message}")
    return json.loads(result.stdout or "null")


def run_text(command: list[str]) -> str:
    if shutil.which(command[0]) is None:
        raise RuntimeError(f"Commande introuvable : {command[0]}")
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    if result.returncode != 0:
        message = result.stderr.strip() or f"code de retour {result.returncode}"
        raise RuntimeError(f"{' '.join(command)} : {message}")
    return result.stdout
