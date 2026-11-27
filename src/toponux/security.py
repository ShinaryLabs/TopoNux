"""Protect the local web server against requests forged by other websites."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

ALLOWED_HOSTS_VARIABLE = "TOPONUX_ALLOWED_HOSTS"
_LOOPBACK_NAMES = {"localhost", "ip6-localhost", "ip6-loopback"}
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def is_loopback(host: str) -> bool:
    """Return True when the listen address stays on the local machine."""
    name = host.strip().lower()
    if name in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def is_allowed_host(header: str) -> bool:
    """Validate a ``Host`` header to block DNS rebinding.

    Rebinding needs a domain name controlled by the attacker, so IP literals,
    loopback names and explicitly configured names are the only accepted values.
    """
    try:
        name = urlsplit(f"//{header}").hostname
    except ValueError:
        return False
    if not name:
        return False
    configured = os.environ.get(ALLOWED_HOSTS_VARIABLE, "").lower().split(",")
    if name in _LOOPBACK_NAMES or name in configured:
        return True
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return False
    return True


async def guard_request(request: Request, call_next):
    """Reject unknown hosts and state-triggering requests from another origin."""
    host = request.headers.get("host", "")
    if not is_allowed_host(host):
        return JSONResponse({"detail": "Host not allowed."}, status_code=400)
    origin = request.headers.get("origin")
    unsafe = request.method not in _SAFE_METHODS
    if unsafe and origin is not None and urlsplit(origin).netloc.lower() != host.lower():
        return JSONResponse({"detail": "Cross-origin request refused."}, status_code=403)
    return await call_next(request)
