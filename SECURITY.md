# Security policy

## Reporting a vulnerability

Please do not open a public issue. Use the **Report a vulnerability** button in the **Security** tab of the GitHub repository.

Do not attach real snapshots, firewall rules or addresses from a production network.

## Scope

Toponux is a local, single-user tool without authentication or TLS. It is meant to listen on loopback.
Issues that let a remote website or host read collected data, trigger probes, or make Toponux modify the system are in scope.

Running with `--allow-remote` or as root widens the exposure by design, as described in `README.md`.

## Supported versions

Only the latest version of the `main` branch receives fixes.
