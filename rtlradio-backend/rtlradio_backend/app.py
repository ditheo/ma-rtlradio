from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import dab, devices, favorites, fm, fm_catalog, stations

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ADMIN_HTML = STATIC_DIR / "admin.html"

app = FastAPI(
    title="RTL-SDR Radio Backend",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fm.router)
app.include_router(devices.router)
app.include_router(dab.router)
app.include_router(stations.router)
app.include_router(favorites.router)
app.include_router(fm_catalog.router)

if STATIC_DIR.exists() and STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/admin", include_in_schema=False)
async def admin_ui():
    if not ADMIN_HTML.exists():
        raise HTTPException(status_code=404, detail=f"admin page not found: {ADMIN_HTML}")
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
            "/stations",
            "/stations/fm",
            "/favorites",
            "/dab/scan/{block}",
            "/fm/catalog/countries",
            "/fm/catalog/states/{countrycode}",
            "/fm/catalog/stations",
            "/fm/catalog/import",
        ],
    }
