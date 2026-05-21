import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ..services.rtl_fm_service import RtlFmService

router = APIRouter()
_svc = RtlFmService()

@router.get("/stream/{frequency}")
async def stream_fm(frequency: float):
    """Stream FM audio from the given frequency (MHz)."""
    try:
        return StreamingResponse(
            _svc.stream(frequency),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/tune/{frequency}")
async def tune(frequency: float):
    """Tune to a frequency without streaming (fire and forget)."""
    await _svc.tune(frequency)
    return {"tuned": frequency}
