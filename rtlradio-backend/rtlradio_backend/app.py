from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .api import fm, devices, dab, stations, favorites

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="RTL-SDR Radio Backend",
    version="0.3.0",
)

app.include_router(fm.router)
app.include_router(devices.router)
app.include_router(dab.router)
app.include_router(stations.router)
app.include_router(favorites.router)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/admin", include_in_schema=False)
async def admin_ui():
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/")
async def root():
    return {
        "name": "RTL-SDR Radio Backend",
        "status": "ok",
        "admin_ui": "/admin",
        "routes": [
            "/",
            "/admin",
            "/stations",
            "/stations/dab",
            "/stations/fm",
            "/favorites",
            "/favorites/resolve/{alias}",
            "/favorites/play/{alias}",
            "/dab/scan/{block}",
            "/dab/status",
            "/dab/mux",
            "/dab/play/{station_id}",
            "/stream/fm/{frequency}",
        ],
    }
