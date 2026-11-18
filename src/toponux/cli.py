import ipaddress

import typer
import uvicorn

app = typer.Typer(help="Cartographie interactive de la configuration réseau Linux.")

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
    host: str = typer.Option("127.0.0.1", help="Adresse d'écoute locale."),
    port: int = typer.Option(8765, min=1, max=65535, help="Port HTTP."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Ne pas ouvrir le navigateur automatiquement."),
    allow_remote: bool = typer.Option(
        False,
        "--allow-remote",
        help="Autoriser une écoute non locale. Les sondes réseau deviennent joignables par le réseau.",
    ),
):
    """Démarre Toponux et ouvre l'interface web."""
    loopback = _is_loopback(host)
    if not loopback and not allow_remote:
        typer.echo(
            f"Refus d'écouter sur {host} : les outils de diagnostic deviendraient "
            "utilisables depuis le réseau. Relance avec --allow-remote pour accepter ce risque.",
            err=True,
        )
        raise typer.Exit(code=1)
    url = f"http://{host}:{port}" if ":" not in host else f"http://[{host}]:{port}"
    typer.echo(f"Toponux disponible sur {url}")
    if not loopback:
        typer.echo(
            "Attention : interface exposée hors loopback. Toute machine pouvant joindre "
            "ce port peut lancer des sondes réseau via Toponux.",
            err=True,
        )
    if not no_browser and loopback:
        import threading
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("toponux.main:app", host=host, port=port, log_level="warning")
