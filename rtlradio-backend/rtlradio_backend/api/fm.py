from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from ..services.rtl_fm_service import RtlFmService
from ..services import radio_state

router = APIRouter(prefix="/stream/fm", tags=["fm"])
_svc = RtlFmService()
radio_state.fm_service = _svc


@router.get("/{frequency}")
async def stream_fm(request: Request, frequency: float):
    try:
        async with radio_state.radio_lock:
            if radio_state.dab_service is not None:
                await radio_state.dab_service.stop()
            radio_state.active_mode = "fm"

        return StreamingResponse(
            _svc.stream(frequency),
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
