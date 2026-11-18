from datetime import datetime, timezone


def collect_snapshot(collectors: dict) -> dict:
    """Collect each subsystem independently so one failure doesn't hide the others.

    A failing or empty collector yields a safe default: callers never receive
    ``None``, which would break the JSON contract consumed by the web UI.
    """
    defaults = {"interfaces": list}
    snapshot = {"collected_at": datetime.now(timezone.utc).isoformat(), "errors": {}}
    for key, collector in collectors.items():
        default = defaults.get(key, dict)()
        try:
            value = collector()
        except Exception as exc:  # surfaced in UI; collector remains read-only
            value = None
            snapshot["errors"][key] = str(exc)
        snapshot[key] = default if value is None else value
    return snapshot
