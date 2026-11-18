from .common import run_json


def collect_routes() -> dict:
    return {
        "ipv4": run_json(["ip", "-j", "-4", "route", "show", "table", "all"]),
        "ipv6": run_json(["ip", "-j", "-6", "route", "show", "table", "all"]),
    }
