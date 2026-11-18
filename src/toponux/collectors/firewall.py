from __future__ import annotations

import shutil
from .common import run_json, run_text


def collect_firewall() -> dict:
    """Collect firewall state without changing it. Prefer nftables JSON.

    Every backend returns its payload under "rules" so the web layer has a
    single contract. "rules" is absent when no backend could be read.
    """
    if shutil.which("nft"):
        try:
            return {"backend": "nftables", "rules": run_json(["nft", "-j", "list", "ruleset"])}
        except (RuntimeError, ValueError) as exc:
            nft_error = str(exc)
    else:
        nft_error = "nft non installé"

    if shutil.which("iptables-save"):
        try:
            v4 = run_text(["iptables-save"])
            v6 = run_text(["ip6tables-save"]) if shutil.which("ip6tables-save") else ""
            return {"backend": "iptables", "rules": {"ipv4": v4, "ipv6": v6}, "nft_error": nft_error}
        except RuntimeError as exc:
            return {"backend": "unavailable", "error": str(exc), "nft_error": nft_error}

    return {"backend": "unavailable", "error": "Ni nft ni iptables-save ne sont disponibles", "nft_error": nft_error}
