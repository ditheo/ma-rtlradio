from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import fm, devices, dab, stations, favorites

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ADMIN_HTML = STATIC_DIR / "admin.html"

app = FastAPI(
    title="RTL-SDR Radio Backend",
    version="0.3.0",
)

app.include_router(fm.router)
app.include_router(devices.router)
app.include_router(dab.router)
app.include_router(stations.router)
app.include_router(favorites.router)

if STATIC_DIR.exists() and STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/admin", include_in_schema=False)
async def admin_ui():
    if not ADMIN_HTML.exists():
        raise HTTPException(
            status_code=404,
            detail=f"admin page not found: {ADMIN_HTML}",
        )
    return FileResponse(ADMIN_HTML)


@app.get("/")
async def root():
    return {
        "name": "RTL-SDR Radio Backend",
        "status": "ok",
        "admin_ui": "/admin",
        "routes": [
            "/",
            "/admin",
            "/static/admin.html",
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
