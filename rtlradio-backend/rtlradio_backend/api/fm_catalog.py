from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..services import radio_state
from ..services.radiobrowser_service import RadioBrowserService

router = APIRouter(prefix="/fm/catalog", tags=["fm-catalog"])
_rb = RadioBrowserService()


class ImportStationRequest(BaseModel):
    stationuuid: str
    name: str
    countrycode: str | None = None
    country: str | None = None
    state: str | None = None
    language: str | None = None
    tags: str | None = None
    codec: str | None = None
    bitrate: int | None = None
    homepage: str | None = None
    favicon: str | None = None
    url: str | None = None
    url_resolved: str | None = None


class ImportStationsRequest(BaseModel):
    items: list[ImportStationRequest] = Field(default_factory=list)


@router.get("/countries")
async def fm_catalog_countries():
    try:
        return {"items": await _rb.countries()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/states/{countrycode}")
async def fm_catalog_states(countrycode: str):
    try:
        return {"items": await _rb.states(countrycode)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stations")
async def fm_catalog_stations(
    countrycode: str | None = Query(default=None),
    state: str | None = Query(default=None),
    name: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    try:
        items = await _rb.stations(
            countrycode=countrycode,
            state=state,
            name=name,
            limit=limit,
        )
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/import")
async def fm_catalog_import(payload: ImportStationsRequest):
    try:
        if radio_state.storage_service is None:
            raise RuntimeError("storage service not configured")

        saved: list[dict[str, Any]] = []
        for item in payload.items:
            station_id = f"fmcatalog:{item.stationuuid}"
            station = {
                "id": station_id,
                "type": "fm",
                "source": "radio-browser",
                "name": item.name,
                "short_name": item.name[:12],
                "frequency": None,
                "countrycode": item.countrycode,
                "country": item.country,
                "state": item.state,
                "language": item.language,
                "tags": item.tags,
                "codec": item.codec,
                "bitrate": item.bitrate,
                "homepage": item.homepage,
                "favicon": item.favicon,
                "url": item.url,
                "url_resolved": item.url_resolved,
                "stream_path": item.url_resolved or item.url,
                "stationuuid": item.stationuuid,
            }
            saved.append(await radio_state.storage_service.upsert_station("fm", station))

        return {"count": len(saved), "items": saved}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
