from fastapi import FastAPI
from .api import fm, devices, dab

app = FastAPI(title="RTL-SDR Radio Backend", version="0.1.0")
app.include_router(fm.router, prefix="/fm", tags=["FM"])
app.include_router(devices.router, prefix="/devices", tags=["Devices"])
app.include_router(dab.router, prefix="/dab", tags=["DAB"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
