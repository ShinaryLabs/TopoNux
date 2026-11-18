from datetime import datetime, timezone


def collect_snapshot(collectors: dict) -> dict:
    """Collect each subsystem independently so one failure doesn't hide the others."""
    snapshot = {"collected_at": datetime.now(timezone.utc).isoformat(), "errors": {}}
    for key, collector in collectors.items():
        try:
            snapshot[key] = collector()
        except Exception as exc:  # surfaced in UI; collector remains read-only
            snapshot[key] = [] if key == "interfaces" else {}
            snapshot["errors"][key] = str(exc)
    return snapshot
