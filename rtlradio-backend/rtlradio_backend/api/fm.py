from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from ..services.rtl_fm_service import RtlFmService
import logging

LOGGER = logging.getLogger(__name__)
router = APIRouter()
_svc = RtlFmService()


@router.get("/stream/{frequency}")
async def stream_fm(request: Request, frequency: float):
    try:
        LOGGER.warning("incoming stream request freq=%s client=%s", frequency, request.client)
        return StreamingResponse(
            _svc.stream(frequency),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )
    except Exception as exc:
        LOGGER.exception("stream endpoint failed for freq=%s: %s", frequency, exc)
        raise HTTPException(status_code=500, detail=str(exc))
