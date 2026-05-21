from fastapi import FastAPI
from .api import fm, devices, dab, stations, favorites

app = FastAPI(
    title="RTL-SDR Radio Backend",
    version="0.3.0",
)

app.include_router(fm.router)
app.include_router(devices.router)
app.include_router(dab.router)
app.include_router(stations.router)
app.include_router(favorites.router)


@app.get("/")
async def root():
    return {
        "name": "RTL-SDR Radio Backend",
        "status": "ok",
        "routes": [
            "/",
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
