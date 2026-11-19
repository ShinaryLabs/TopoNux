from toponux.collectors.common import run_json


def collect_neighbors() -> list[dict]:
    """Read the ARP/NDP cache: IPv4 and IPv6 link-layer neighbours.

    Read-only: ``ip neigh show`` inspects the kernel neighbour table.
    Docker-related filtering happens in the graph view, not here.
    """
    return run_json(["ip", "-j", "neigh", "show"])
