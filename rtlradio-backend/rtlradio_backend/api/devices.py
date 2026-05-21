from fastapi import APIRouter
from ..services.discovery import discover_devices

router = APIRouter()

@router.get("/")
async def list_devices():
    """Return a list of detected RTL-SDR USB devices."""
    return {"devices": discover_devices()}
