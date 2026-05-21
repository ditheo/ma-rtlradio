from fastapi import FastAPI
from .api import fm, devices, dab, stations

app = FastAPI(
    title="RTL-SDR Radio Backend",
    version="0.2.0",
)

app.include_router(fm.router)
app.include_router(devices.router)
app.include_router(dab.router)
app.include_router(stations.router)


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
            "/dab/scan/{block}",
            "/dab/status",
            "/dab/mux",
            "/dab/play/{station_id}",
            "/stream/fm/{frequency}",
        ],
    }
