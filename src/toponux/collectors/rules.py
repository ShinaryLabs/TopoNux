from .common import run_json


def collect_policy_rules() -> dict:
    return {
        "ipv4": run_json(["ip", "-j", "-4", "rule", "show"]),
        "ipv6": run_json(["ip", "-j", "-6", "rule", "show"]),
    }
