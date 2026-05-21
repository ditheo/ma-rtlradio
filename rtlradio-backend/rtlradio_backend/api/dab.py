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
        match = None

        for st in stations:
            station_name = (st.get("name") or "").strip()
            short_name = (st.get("short_name") or "").strip()

            if station_name.casefold() == wanted or short_name.casefold() == wanted:
                match = st
                break

        if not match:
            partial_matches = []
            for st in stations:
                station_name = (st.get("name") or "").strip()
                short_name = (st.get("short_name") or "").strip()

                if wanted in station_name.casefold() or wanted in short_name.casefold():
                    partial_matches.append({
                        "id": st.get("id"),
                        "name": st.get("name"),
                        "short_name": st.get("short_name"),
                        "block": st.get("block"),
                        "url_mp3": st.get("url_mp3"),
                    })

            if partial_matches:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": f"station not found with exact name: {name}",
                        "matches": partial_matches[:10],
                    },
                )

            return JSONResponse(
                status_code=404,
                content={"error": f"station not found: {name}"},
            )

        station_id = match.get("id")
        if not station_id:
            raise RuntimeError(f"matched station has no id: {name}")

        stream = await _svc.proxy_stream_by_station_id(station_id)
        return StreamingResponse(
            stream,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
                "X-Station-Id": station_id,
                "X-Station-Name": match.get("name") or "",
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "name": name},
        )
