from fastapi import FastAPI
from .api import fm, devices, dab

app = FastAPI(
    title="RTL-SDR Radio Backend",
    version="0.1.0",
)

app.include_router(fm.router)
app.include_router(devices.router)
app.include_router(dab.router)


@app.get("/")
async def root():
    return {
        "name": "RTL-SDR Radio Backend",
        "status": "ok",
        "routes": [
            "/",
            "/fm/...",
            "/devices/...",
            "/dab/info",
            "/dab/status",
            "/dab/scan/{block}",
            "/dab/start/{block}",
            "/dab/stop",
            "/dab/mux",
        ],
    }
