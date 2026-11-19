import ipaddress

import typer
import uvicorn

app = typer.Typer(help="Interactive Linux network configuration viewer.")

_LOOPBACK_NAMES = {"localhost", "ip6-localhost", "ip6-loopback"}


def _is_loopback(host: str) -> bool:
    """Return True when the listen address stays on the local machine."""
    name = host.strip().lower()
    if name in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


@app.callback(invoke_without_command=True)
def start(
    host: str = typer.Option("127.0.0.1", help="Local listen address."),
    port: int = typer.Option(8765, min=1, max=65535, help="HTTP port."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open the browser automatically."),
    allow_remote: bool = typer.Option(
        False,
        "--allow-remote",
        help="Allow a non-local listen address. Diagnostic probes become reachable from the network.",
    ),
):
    """Start Toponux and open the web interface."""
    loopback = _is_loopback(host)
    if not loopback and not allow_remote:
        typer.echo(
            f"Refusing to listen on {host}: the diagnostic tools would become "
            "reachable from the network. Re-run with --allow-remote to accept this risk.",
            err=True,
        )
        raise typer.Exit(code=1)
    url = f"http://{host}:{port}" if ":" not in host else f"http://[{host}]:{port}"
    typer.echo(f"Toponux available at {url}")
    if not loopback:
        typer.echo(
            "Warning: listening outside loopback. Any machine that can reach "
            "this port can launch network probes through Toponux.",
            err=True,
        )
    if not no_browser and loopback:
        import threading
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("toponux.main:app", host=host, port=port, log_level="warning")
