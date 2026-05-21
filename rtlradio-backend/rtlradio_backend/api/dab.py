from fastapi import APIRouter, HTTPException
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
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "station_id": station_id},
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
            is_exact = station_name.casefold() == wanted or short_name.casefold() == wanted
            is_partial = wanted in station_name.casefold() or wanted in short_name.casefold()

            if is_exact and has_stream and exact_playable is None:
                exact_playable = st
                break

            if is_exact and not has_stream and exact_unplayable is None:
                exact_unplayable = {
                    "id": st.get("id"),
                    "name": st.get("name"),
                    "short_name": st.get("short_name"),
                    "block": st.get("block"),
                    "url_mp3": st.get("url_mp3"),
                    "error": "station exists but is not playable",
                }

            if is_partial and has_stream:
                partial_playable.append({
                    "id": st.get("id"),
                    "name": st.get("name"),
                    "short_name": st.get("short_name"),
                    "block": st.get("block"),
                })

        if exact_playable is None:
            if exact_unplayable is not None:
                return JSONResponse(status_code=404, content=exact_unplayable)

            if partial_playable:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": f"station not found with exact playable name: {name}",
                        "matches": partial_playable[:10],
                    },
                )

            return JSONResponse(
                status_code=404,
                content={"error": f"station not found: {name}"},
            )

        station_id = exact_playable.get("id")
        if not station_id:
            return JSONResponse(
                status_code=500,
                content={"error": f"matched station has no id: {name}"},
            )

        stream = await _svc.proxy_stream_by_station_id(station_id)
        return StreamingResponse(
            stream,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
                "X-Station-Id": station_id,
                "X-Station-Name": exact_playable.get("name") or "",
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "name": name},
        )
