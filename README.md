# Toponux

Toponux is a local Linux tool that maps the network configuration in **read-only** mode.

## Principles

- No network configuration is modified.
- No scan commands, no test packets and no connections to remote hosts.
- Local collection through query-only commands (`ip -j`, `nft list ruleset`, `iptables-save`).
- Information that cannot be accessed is reported; Toponux does not try to bypass permissions.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Launch

```bash
toponux
```

Open http://127.0.0.1:8765 if the browser does not open automatically.

To read firewall rules, you may launch Toponux with the required permissions:

```bash
sudo .venv/bin/toponux
```

Even with elevated privileges, Toponux remains strictly read-only.

By default Toponux listens on loopback only. Listening on another address requires the explicit `--allow-remote` flag, because the diagnostic tools would then be reachable from the network:

```bash
toponux --host 0.0.0.0 --allow-remote
```

## Views

- **Global view**: local machine, main IP interfaces, active virtual bridges and default gateways.
- **Interfaces**: full inventory, including loopback, veth and DOWN interfaces.
- **Routing**: all IPv4/IPv6 routes and policy routing rules.
- **Firewall**: collection status and available rules.
- **Raw data**: complete JSON snapshot.

The global view intentionally hides local, broadcast and multicast routes as well as veth interfaces. Details remain available in the dedicated views.

## Tests

```bash
pip install -e '.[dev]'
pytest
```


## Diagnostic tools (V0.3)

The **Diagnostic** tab offers a bounded ping, a traceroute/tracepath and a TCP connection test. These operations intentionally generate network traffic, but do not modify any local configuration. The kernel's chosen route is queried with `ip route get`.

The TCP test reports the result actually observed; it does not claim to identify the responsible firewall rule on its own. A timeout may have several causes. The traceroute uses `tracepath` when available, otherwise `traceroute`.
