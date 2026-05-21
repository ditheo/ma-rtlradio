from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..services.storage_service import StorageService
from ..services import radio_state

router = APIRouter(prefix="/favorites", tags=["favorites"])

if radio_state.storage_service is None:
    radio_state.storage_service = StorageService()


class FavoriteCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=120)
    station_id: str = Field(..., min_length=1, max_length=200)


@router.get("")
async def get_favorites():
    try:
        items = await radio_state.storage_service.get_favorites()
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("")
async def add_favorite(payload: FavoriteCreate):
    try:
        data = await radio_state.storage_service.upsert_favorite(
            payload.alias,
            payload.station_id,
        )
        return {
            "ok": True,
            "favorites_count": len(data.get("favorites", [])),
            "data": data,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{alias:path}")
async def delete_favorite(alias: str):
    try:
        data = await radio_state.storage_service.delete_favorite(alias)
        return {
            "ok": True,
            "favorites_count": len(data.get("favorites", [])),
            "data": data,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/resolve/{alias:path}")
async def resolve_favorite(alias: str):
    try:
        favorite = await radio_state.storage_service.get_favorite(alias)
        if not favorite:
            raise HTTPException(status_code=404, detail=f"favorite not found: {alias}")

        return {
            "ok": True,
            "alias": favorite.get("alias"),
            "station_id": favorite.get("station_id"),
            "station_type": favorite.get("station_type"),
            "target_path": favorite.get("target_path"),
            "source_name": favorite.get("source_name"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/play/{alias:path}")
async def play_favorite(alias: str):
    try:
        favorite = await radio_state.storage_service.get_favorite(alias)
        if not favorite:
            raise HTTPException(status_code=404, detail=f"favorite not found: {alias}")

        target_path = favorite.get("target_path")
        if not target_path:
            raise HTTPException(status_code=500, detail=f"favorite has no target_path: {alias}")

        return RedirectResponse(url=target_path, status_code=307)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
