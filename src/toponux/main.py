from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from toponux.api.routes import router

WEB_DIR = Path(__file__).parent / "web"
app = FastAPI(title="Toponux", docs_url="/api/docs")
app.include_router(router)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")
