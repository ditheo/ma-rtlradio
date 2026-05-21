from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.storage_service import StorageService
from ..services import radio_state

router = APIRouter(prefix="/stations", tags=["stations"])

if radio_state.storage_service is None:
    radio_state.storage_service = StorageService()


class FmStationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    frequency: float = Field(..., gt=50.0, lt=200.0)


@router.get("")
async def get_all_stations():
    try:
        return await radio_state.storage_service.get_all_stations()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dab")
async def get_dab_stations():
    try:
        stations = await radio_state.storage_service.get_dab_stations()
        return {"count": len(stations), "items": stations}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fm")
async def get_fm_stations():
    try:
        stations = await radio_state.storage_service.get_fm_stations()
        return {"count": len(stations), "items": stations}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fm")
async def add_fm_station(payload: FmStationCreate):
    try:
        data = await radio_state.storage_service.add_fm_station(payload.name, payload.frequency)
        return {"ok": True, "fm_count": len(data.get("fm", [])), "data": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{station_id:path}")
async def delete_station(station_id: str):
    try:
        data = await radio_state.storage_service.delete_station(station_id)
        return {"ok": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
