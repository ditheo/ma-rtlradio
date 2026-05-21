from fastapi import APIRouter, HTTPException
from ..services.dab_service import DabService

router = APIRouter()
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
