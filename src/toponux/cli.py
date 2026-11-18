import socket
import typer
import uvicorn

app = typer.Typer(help="Cartographie interactive de la configuration réseau Linux.")

@app.callback(invoke_without_command=True)
def start(
    host: str = typer.Option("127.0.0.1", help="Adresse d'écoute locale."),
    port: int = typer.Option(8765, min=1, max=65535, help="Port HTTP."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Ne pas ouvrir le navigateur automatiquement."),
):
    """Démarre Toponux et ouvre l'interface web."""
    url = f"http://{host}:{port}"
    typer.echo(f"Toponux disponible sur {url}")
    if not no_browser and host in {"127.0.0.1", "localhost"}:
        import threading, webbrowser
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("toponux.main:app", host=host, port=port, log_level="warning")
