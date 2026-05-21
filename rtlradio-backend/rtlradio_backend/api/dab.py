from fastapi import APIRouter

router = APIRouter()

@router.get("/stations")
async def dab_stations():
    """DAB+ station list — stub, reserved for future implementation."""
    return {"stations": [], "message": "DAB+ not yet implemented"}
