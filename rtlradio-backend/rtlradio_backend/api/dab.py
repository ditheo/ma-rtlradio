from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
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


@router.get("/scan/{block}")
async def scan_block(block: str):
    try:
        return await _svc.scan(block)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/start/{block}")
async def start_block(block: str, port: int = Query(default=7979, ge=1025, le=65535)):
    try:
        async with radio_state.radio_lock:
            if radio_state.fm_service is not None:
                await radio_state.fm_service.stop()
            result = await _svc.start_web(block, port)
            radio_state.active_mode = "dab"
            return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/stop")
async def stop_dab():
    try:
        return await _svc.stop()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
async def dab_status():
    try:
        return await _svc.status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/mux")
async def dab_mux():
    try:
        return await _svc.mux()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/programmes")
async def dab_programmes():
    try:
        data = await _svc.mux()
        payload = data.get("json") or {}
        services = payload.get("services") or []

        programmes = []
        for svc in services:
            sid = svc.get("sid")
            label = ((svc.get("label") or {}).get("label")) or sid
            shortlabel = ((svc.get("label") or {}).get("shortlabel")) or label
            pty = svc.get("ptystring")
            url_mp3 = svc.get("url_mp3")

            if sid and url_mp3:
                programmes.append({
                    "name": label,
                    "short_name": shortlabel,
                    "sid": sid,
                    "type": pty,
                    "stream_path": f"/dab/play/{sid}",
                    "stream_url": f"/dab/play/{sid}",
                })

        return {
            "running": data.get("running", False),
            "block": data.get("block"),
            "port": data.get("port"),
            "ensemble": ((payload.get("ensemble") or {}).get("label") or {}).get("label"),
            "programmes": programmes,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/play/{sid}")
async def dab_play(sid: str):
    try:
        stream = await _svc.proxy_stream(sid)
        return StreamingResponse(
            stream,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "sid": sid})
