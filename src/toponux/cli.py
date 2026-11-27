import os
from typing import Annotated

import typer
import uvicorn

from toponux.security import ALLOWED_HOSTS_VARIABLE, is_loopback

app = typer.Typer(help="Interactive Linux network configuration viewer.")


@app.callback(invoke_without_command=True)
def start(
    host: str = typer.Option("127.0.0.1", help="Local listen address."),
    port: int = typer.Option(8765, min=1, max=65535, help="HTTP port."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open the browser automatically."),
    allow_remote: bool = typer.Option(
        False,
        "--allow-remote",
        help="Allow a non-local listen address. No authentication: the inventory and probes are exposed.",
    ),
    allowed_host: Annotated[
        list[str] | None,
        typer.Option("--allowed-host", help="Extra DNS name accepted in the Host header. Repeatable."),
    ] = None,
):
    """Start Toponux and open the web interface."""
    loopback = is_loopback(host)
    if not loopback and not allow_remote:
        typer.echo(
            f"Refusing to listen on {host}: the network inventory and diagnostic tools would become "
            "reachable from the network without authentication. Re-run with --allow-remote to accept this risk.",
            err=True,
        )
        raise typer.Exit(code=1)
    url = f"http://{host}:{port}" if ":" not in host else f"http://[{host}]:{port}"
    typer.echo(f"Toponux available at {url}")
    if not loopback:
        typer.echo(
            "Warning: listening outside loopback without authentication. Any machine that can reach "
            "this port can read the network inventory and launch network probes through Toponux.",
            err=True,
        )
    is_root = os.geteuid() == 0
    if is_root:
        typer.echo(
            "Warning: running as root without authentication. Every local user can read what root sees "
            "through this port. The browser will not be opened.",
            err=True,
        )
    os.environ[ALLOWED_HOSTS_VARIABLE] = ",".join([host, *(allowed_host or [])])
    if not no_browser and loopback and not is_root:
        import threading
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("toponux.main:app", host=host, port=port, log_level="warning")
