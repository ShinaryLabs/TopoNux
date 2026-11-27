from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from toponux.api.routes import router
from toponux.security import guard_request

WEB_DIR = Path(__file__).parent / "web"
# Interactive API docs load third-party scripts from a CDN, so they stay disabled.
app = FastAPI(title="Toponux", docs_url=None, redoc_url=None, openapi_url=None)
app.middleware("http")(guard_request)
app.include_router(router)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")
