# Toponux

Toponux is a local Linux tool that maps the network configuration in **read-only** mode.

## Principles

- No network configuration is modified.
- Local collection through query-only commands (`ip -j`, `ss`, `nft list ruleset`, `iptables-save`).
- Active diagnostics (ping, traceroute, TCP test and subnet scan) run only when explicitly triggered and do not modify addresses, routes, interfaces or firewall rules.
- Information that cannot be accessed is reported; Toponux does not try to bypass permissions.

## Requirements

- Linux, Python 3.10 or later.
- Required commands: `ip` (iproute2) and `ss`.
- Optional commands: `bridge`, `nft` or `iptables-save`/`ip6tables-save`, `ping`, `tracepath` or `traceroute`. A missing tool only disables the matching information.
- Optional OUI database for vendor names (for example the `ieee-data` package).

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

To run it in the background, use the `Makefile` (it creates `.venv` and installs Toponux on first start):

```bash
make start    # start (options: PORT=9000 ARGS=--no-browser)
make status
make restart
make stop
```

With elevated privileges (see the risk above), install first without `sudo`, then run `sudo make start` and `sudo make stop`. The browser is not opened and the log is readable by root only.

The process ID and output are kept in `.toponux.pid` and `.toponux.log`, both ignored by Git.

Toponux runs as a normal user. Reading firewall rules usually needs root or `CAP_NET_ADMIN`; without it the Firewall tab reports the error and everything else works.

You may run it with elevated privileges, but understand the risk first:

```bash
sudo .venv/bin/toponux
```

The web server has **no authentication**. While it runs as root, every local user and process can read the firewall rules, sockets and process names through the port, and launch probes. Stop it as soon as you are done. As root, the browser is not opened automatically: open the URL from your normal session.

By default Toponux listens on loopback only. Listening on another address requires the explicit `--allow-remote` flag:

```bash
toponux --host 0.0.0.0 --allow-remote --allowed-host server.example
```

Anyone who can reach the port can then read the whole network inventory and launch probes. Use it only on a trusted network, or prefer an SSH tunnel: `ssh -L 8765:127.0.0.1:8765 user@server`.

## Security

- Requests are accepted only when the `Host` header is an IP address, a loopback name, the `--host` value or a name given with `--allowed-host` (protection against DNS rebinding).
- `POST` requests coming from another web origin are refused.
- The interactive API documentation is disabled because it loads scripts from a CDN.
- There is no authentication and no TLS. See `SECURITY.md` to report a vulnerability.
- Snapshots, exports and saved baselines contain sensitive data (addresses, MAC addresses, connections, process names, firewall rules). Review them before sharing.

**Active probes:** ping, traceroute, TCP test and subnet scan send packets. The subnet scan covers up to 512 IPv4 hosts on every interface that is not down, including VPN and virtual interfaces. Only probe networks you are allowed to probe.

## Views

- **Overview**: local machine, main IP interfaces, bridges, bonds, VLAN devices and default gateways.
- **Interfaces**: full inventory, including loopback, veth and DOWN interfaces.
- **Neighbours**: ARP/NDP cache grouped by interface and MAC.
- **Ports**: TCP/UDP listening sockets and established connections to remote peers.
- **Changes**: compare the current snapshot with a baseline saved in the browser.
- **Routing**: all IPv4/IPv6 routes and policy routing rules.
- **Firewall**: collection status and available rules.
- **Network tools**: bounded active diagnostics and the local IPv6 inspector.
- **Data sources**: commands, fields, permissions and limits for every dataset.
- **Raw data**: complete JSON snapshot.

The Overview intentionally hides local, broadcast and multicast routes as well as veth interfaces. Details remain available in the dedicated views.

## Interface

The web interface follows the design system described in `DESIGN.md`. All colours, spacing, radii and typography values are centralised as CSS custom properties at the top of `src/toponux/web/style.css`; pages and components reference those tokens instead of hard-coded values.

- Status colours carry meaning: green for an operational state, amber for a warning or an unknown state, red for an error, blue for information and navigation. Badges always combine a tinted background with a readable label.
- Buttons, fields, tables, badges and panels share one set of variants across every tab.
- The topology and firewall graphs use the same tokens, with white text on saturated fills.
- Tabs are reachable with the keyboard: `Tab` enters the tab list, then `ArrowLeft`, `ArrowRight`, `Home` and `End` move between views. A skip link jumps straight to the content.
- Search fields have accessible labels, focus is always visible, and animations are disabled when the system requests reduced motion.
- Layouts adapt to desktop, tablet and mobile widths; wide tables scroll horizontally instead of truncating data.
- No font, script or stylesheet is loaded from the network: everything is served locally.

## Tests

```bash
pip install -e '.[dev]'
pytest
```

The same checks run in CI, through `uv`:

```bash
uv sync --extra dev --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```


## Snapshot comparison

The **Changes** tab compares the current snapshot with a baseline saved in the browser (`localStorage`). It lists added and removed interfaces, neighbours, routes, listening sockets and established connections. No data leaves the machine and no network packet is sent.

## Ports and connections

The **Ports** tab reads the current TCP/UDP socket table with:

```bash
ss -H -t -u -a -n -p
```

It lists listening sockets and established connections whose peer is not the local machine. Loopback traffic and connections to one of the machine's own addresses are hidden from the connection table.

Socket listing normally works as an unprivileged user. Process names may be missing for sockets owned by other users unless Toponux runs with enough privilege. The command only inspects the current network namespace; it does not open, close or modify a socket.

## Network tools

The **Network tools** tab offers a bounded ping, a traceroute/tracepath and a TCP connection test. These operations intentionally generate network traffic, but do not modify any local configuration. The kernel's chosen route is queried with `ip route get`; a DNS name is first resolved with the system resolver.

The TCP test reports the result actually observed; it does not claim to identify the responsible firewall rule on its own. A timeout may have several causes. The traceroute uses `tracepath` when available, otherwise `traceroute`.

The **IPv6 address inspector** is different: it parses one IPv6 address locally with Python's `ipaddress` module. It reports the address type, scope, optional prefix and the important header flags. It sends no packet and contacts no remote host.

## License

MIT, see `LICENSE`.

The web interface bundles [Cytoscape.js](https://js.cytoscape.org/) 3.30.4 (MIT, Copyright The Cytoscape Consortium) in `src/toponux/web/vendor/`.
