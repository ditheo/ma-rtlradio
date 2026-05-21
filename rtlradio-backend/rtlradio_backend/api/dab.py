from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder

from ..services.dab_service import DabService
from ..services import radio_state

DEBUG_DAB_API_VERSION = "dab.py marker v2026-05-21-1717"

router = APIRouter(prefix="/dab", tags=["dab"])
_svc = DabService()
radio_state.dab_service = _svc


def _station_to_plain_dict(st):
    if isinstance(st, dict):
        return dict(st)

    if hasattr(st, "keys"):
        try:
            return {key: st[key] for key in st.keys()}
        except Exception:
            pass

    if hasattr(st, "_mapping"):
        try:
            return dict(st._mapping)
        except Exception:
            pass

    if hasattr(st, "__dict__"):
        try:
            data = {}
            for key, value in vars(st).items():
                if not key.startswith("_"):
                    data[key] = value
            if data:
                return data
        except Exception:
            pass

    try:
        return dict(st)
    except Exception:
        return {"value": str(st)}


def _safe_station_summary(station):
    return {
        "id": str(station.get("id") or ""),
        "type": str(station.get("type") or ""),
        "name": str(station.get("name") or ""),
        "short_name": str(station.get("short_name") or ""),
        "sid": str(station.get("sid") or ""),
        "block": str(station.get("block") or ""),
        "ensemble": str(station.get("ensemble") or ""),
        "genre": str(station.get("genre") or ""),
        "url_mp3": station.get("url_mp3"),
        "stream_path": str(station.get("stream_path") or ""),
        "last_seen": str(station.get("last_seen") or ""),
    }


@router.get("/info")
async def dab_info():
    try:
        data = await _svc.info()
        data["debug_api_version"] = DEBUG_DAB_API_VERSION
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/debug-marker")
async def dab_debug_marker():
    return {
        "ok": True,
        "debug_api_version": DEBUG_DAB_API_VERSION,
        "router_prefix": "/dab",
        "service_class": _svc.__class__.__name__,
    }


@router.post("/scan/{block}")
async def scan_block(block: str):
    try:
        data = await _svc.scan_and_store(block)
        if isinstance(data, dict):
            data["debug_api_version"] = DEBUG_DAB_API_VERSION
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
async def dab_status():
    try:
        return {
            "running": _svc._proc is not None and _svc._proc.returncode is None,
            "block": _svc._block,
            "port": _svc._port,
            "debug_api_version": DEBUG_DAB_API_VERSION,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/mux")
async def dab_mux():
    try:
        data = await _svc.mux()
        if isinstance(data, dict):
            data["debug_api_version"] = DEBUG_DAB_API_VERSION
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/resolve-by-name/{name:path}")
async def dab_resolve_by_name(name: str):
    try:
        if radio_state.storage_service is None:
            raise RuntimeError("storage service not configured")

        raw_stations = await radio_state.storage_service.list_stations("dab")
        stations = [_station_to_plain_dict(st) for st in raw_stations]

        wanted = name.strip().casefold()
        exact_playable = None
        exact_unplayable = None
        partial_playable = []

        for st in stations:
            station_name = str(st.get("name") or "").strip()
            short_name = str(st.get("short_name") or "").strip()
            has_stream = bool(st.get("url_mp3"))

            exact_match = (
                station_name.casefold() == wanted
                or short_name.casefold() == wanted
            )

            partial_match = (
                wanted in station_name.casefold()
                or wanted in short_name.casefold()
            )

            if exact_match and has_stream:
                exact_playable = st
                break

            if exact_match and not has_stream and exact_unplayable is None:
                exact_unplayable = _safe_station_summary(st)
                exact_unplayable["error"] = "station exists but is not playable"
                exact_unplayable["debug_api_version"] = DEBUG_DAB_API_VERSION

            if partial_match and has_stream:
                partial_playable.append(_safe_station_summary(st))

        if exact_playable is None:
            if exact_unplayable is not None:
                return JSONResponse(
                    status_code=404,
                    content=jsonable_encoder(exact_unplayable),
                )

            if partial_playable:
                return JSONResponse(
                    status_code=404,
                    content=jsonable_encoder({
                        "error": f"station not found with exact playable name: {name}",
                        "matches": partial_playable[:10],
                        "debug_api_version": DEBUG_DAB_API_VERSION,
                    }),
                )

            return JSONResponse(
                status_code=404,
                content=jsonable_encoder({
                    "error": f"station not found: {name}",
                    "debug_api_version": DEBUG_DAB_API_VERSION,
                }),
            )

        station_id = str(exact_playable.get("id") or "")
        if not station_id:
            return JSONResponse(
                status_code=500,
                content=jsonable_encoder({
                    "error": f"matched station has no id: {name}",
                    "debug_api_version": DEBUG_DAB_API_VERSION,
                }),
            )

        stream_path = str(exact_playable.get("stream_path") or f"/dab/play/{station_id}")

        payload = {
            "ok": True,
            "query": name,
            "resolved_name": str(exact_playable.get("name") or ""),
            "station_id": station_id,
            "sid": str(exact_playable.get("sid") or ""),
            "block": str(exact_playable.get("block") or ""),
            "ensemble": str(exact_playable.get("ensemble") or ""),
            "genre": str(exact_playable.get("genre") or ""),
            "url_mp3": exact_playable.get("url_mp3"),
            "stream_path": stream_path,
            "play_url": stream_path,
            "debug_api_version": DEBUG_DAB_API_VERSION,
        }

        return JSONResponse(status_code=200, content=jsonable_encoder(payload))
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder({
                "error": str(exc),
                "name": name,
                "debug_api_version": DEBUG_DAB_API_VERSION,
            }),
        )


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
                "X-Debug-Api-Version": DEBUG_DAB_API_VERSION,
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder({
                "error": str(exc),
                "station_id": station_id,
                "debug_api_version": DEBUG_DAB_API_VERSION,
            }),
        )
