from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import traceback

from ..services.dab_service import DabService
from ..services import radio_state

router = APIRouter(prefix="/dab", tags=["dab"])
_svc = DabService()
radio_state.dab_service = _svc


@router.get("/info")
async def dab_info():
    try:
        return await _svc.info()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/scan/{block}")
async def scan_block(block: str):
    try:
        return await _svc.scan_and_store(block)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
async def dab_status():
    try:
        return {
            "running": _svc._proc is not None and _svc._proc.returncode is None,
            "block": _svc._block,
            "port": _svc._port,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/mux")
async def dab_mux():
    try:
        return await _svc.mux()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/play/{station_id:path}")
async def dab_play(station_id: str):
    try:
        stream = await _svc.proxy_stream_by_station_id(station_id)
        return StreamingResponse(
            stream,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
                "X-Station-Id": station_id,
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "station_id": station_id,
                "traceback": traceback.format_exc(),
            },
        )


@router.get("/play-by-name/{name:path}")
async def dab_play_by_name(name: str):
    try:
        if radio_state.storage_service is None:
            raise RuntimeError("storage service not configured")

        stations = await radio_state.storage_service.list_stations("dab")
        wanted = name.strip().casefold()

        exact_playable = None
        exact_unplayable = None
        partial_playable = []

        for st in stations:
            station_name = (st.get("name") or "").strip()
            short_name = (st.get("short_name") or "").strip()
            has_stream = bool(st.get("url_mp3"))

            exact_match = (
                station_name.casefold() == wanted
                or short_name.casefold() 
