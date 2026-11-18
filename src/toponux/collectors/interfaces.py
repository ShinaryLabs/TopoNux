from .common import run_json


def collect_interfaces() -> list[dict]:
    return run_json(["ip", "-j", "address", "show"])
