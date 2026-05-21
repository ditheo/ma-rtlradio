from fastapi import APIRouter, HTTPException, Query
from ..services.dab_service import DabService

router = APIRouter(prefix="/dab", tags=["dab"])
_svc = DabService()


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
        return await _svc.start_web(block, port)
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
