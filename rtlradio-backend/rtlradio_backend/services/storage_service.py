from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StorageService:
    def __init__(self, storage_path: str | None = None) -> None:
        default_path = Path("/config/rtlradio/stations.json")
        self._path = Path(storage_path) if storage_path else default_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _default_data(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "updated_at": _now_iso(),
            "dab": [],
            "fm": [],
            "favorites": [],
        }

    def _ensure_file(self) -> None:
        if not self._path.exists():
            self._write(self._default_data())

    def _read(self) -> dict[str, Any]:
        self._ensure_file()
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = self._default_data()

        data.setdefault("schema_version", 1)
        data.setdefault("updated_at", _now_iso())
        data.setdefault("dab", [])
        data.setdefault("fm", [])
        data.setdefault("favorites", [])
        return data

    def _write(self, data: dict[str, Any]) -> dict[str, Any]:
        data["updated_at"] = _now_iso()
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    async def get_all(self) -> dict[str, Any]:
        return deepcopy(self._read())

    async def list_stations(self, band: str | None = None) -> list[dict[str, Any]]:
        data = self._read()
        if band == "dab":
            return deepcopy(data["dab"])
        if band == "fm":
            return deepcopy(data["fm"])
        return deepcopy(data["dab"] + data["fm"])

    async def get_station_by_id(self, station_id: str) -> dict[str, Any] | None:
        station_id = station_id.strip()
        for station in await self.list_stations():
            if (station.get("id") or "").strip() == station_id:
                return deepcopy(station)
        return None

    async def upsert_station(self, band: str, station: dict[str, Any]) -> dict[str, Any]:
        if band not in {"dab", "fm"}:
            raise ValueError("band must be 'dab' or 'fm'")

        data = self._read()
        items = data[band]

        station = deepcopy(station)
        station["last_seen"] = _now_iso()

        station_id = (station.get("id") or "").strip()
        if not station_id:
            raise ValueError("station id is required")

        existing_index = next(
            (i for i, s in enumerate(items) if (s.get("id") or "").strip() == station_id),
            None,
        )

        if existing_index is None:
            items.append(station)
        else:
            items[existing_index] = {**items[existing_index], **station}

        self._write(data)
        return deepcopy(station)

    async def upsert_dab_stations(
        self,
        block: str,
        ensemble: str | None,
        stations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        data = self._read()
        items = data["dab"]
        saved: list[dict[str, Any]] = []

        for raw in stations:
            sid = str(raw.get("sid") or "").strip()
            if not sid:
                continue

            station_id = str(raw.get("id") or f"dab:{block}:{sid}")
            name = str(raw.get("name") or sid).strip()
            short_name = str(raw.get("short_name") or name[:8]).strip()

            url_mp3 = raw.get("url_mp3")
            if url_mp3 is None and sid:
                url_mp3 = f"/mp3/{sid}"

            stream_path = raw.get("stream_path") or f"/dab/play/{station_id}"

            station = {
                "id": station_id,
                "type": "dab",
                "source": raw.get("source") or "dab-scan",
                "name": name,
                "short_name": short_name,
                "sid": sid,
                "block": block,
                "ensemble": raw.get("ensemble") or ensemble or "",
                "genre": raw.get("genre") or "",
                "bitrate": raw.get("bitrate"),
                "url_mp3": url_mp3,
                "stream_path": stream_path,
                "last_seen": _now_iso(),
            }

            existing_index = next(
                (i for i, s in enumerate(items) if (s.get("id") or "").strip() == station_id),
                None,
            )

            if existing_index is None:
                items.append(station)
            else:
                items[existing_index] = {**items[existing_index], **station}

            saved.append(deepcopy(station))

        self._write(data)
        return saved

    async def add_or_update_fm_station(self, name: str, frequency: float) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("name is required")

        freq = round(float(frequency), 1)
        station = {
            "id": f"fm:{freq:.1f}",
            "type": "fm",
            "source": "manual",
            "name": clean_name,
            "short_name": clean_name[:12],
            "frequency": freq,
            "stream_path": f"/stream/fm/{freq:.1f}",
        }
        return await self.upsert_station("fm", station)

    async def import_fm_catalog_station(self, station: dict[str, Any]) -> dict[str, Any]:
        stationuuid = str(station.get("stationuuid") or "").strip()
        name = str(station.get("name") or "").strip()

        if not stationuuid:
            raise ValueError("stationuuid is required")
        if not name:
            raise ValueError("name is required")

        stream_url = station.get("url_resolved") or station.get("url")
        if not stream_url:
            raise ValueError("station stream url is required")

        item = {
            "id": f"fmcatalog:{stationuuid}",
            "type": "fm",
            "source": "radio-browser",
            "name": name,
            "short_name": name[:12],
            "frequency": None,
            "countrycode": station.get("countrycode"),
            "country": station.get("country"),
            "state": station.get("state"),
            "language": station.get("language"),
            "tags": station.get("tags"),
            "codec": station.get("codec"),
            "bitrate": station.get("bitrate"),
            "homepage": station.get("homepage"),
            "favicon": station.get("favicon"),
            "url": station.get("url"),
            "url_resolved": station.get("url_resolved"),
            "stream_path": stream_url,
            "stationuuid": stationuuid,
        }
        return await self.upsert_station("fm", item)

    async def list_favorites(self) -> list[dict[str, Any]]:
        data = self._read()
        return deepcopy(data["favorites"])

    async def create_favorite(self, alias: str, station_id: str) -> dict[str, Any]:
        alias = alias.strip()
        station_id = station_id.strip()

        if not alias:
            raise ValueError("alias is required")
        if not station_id:
            raise ValueError("station_id is required")

        station = await self.get_station_by_id(station_id)
        if not station:
            raise ValueError(f"station not found: {station_id}")

        target_path = station.get("stream_path")
        if not target_path:
            raise ValueError(f"station has no stream_path: {station_id}")

        data = self._read()
        favorites = data["favorites"]

        record = {
            "alias": alias,
            "station_id": station_id,
            "station_type": station.get("type"),
            "target_path": target_path,
            "updated_at": _now_iso(),
        }

        existing_index = next(
            (i for i, f in enumerate(favorites) if (f.get("alias") or "").casefold() == alias.casefold()),
            None,
        )

        if existing_index is None:
            favorites.append(record)
        else:
            favorites[existing_index] = record

        self._write(data)
        return deepcopy(record)

    async def resolve_favorite(self, alias: str) -> dict[str, Any] | None:
        alias_cf = alias.strip().casefold()
        for item in await self.list_favorites():
            if (item.get("alias") or "").casefold() == alias_cf:
                return deepcopy(item)
        return None

    async def delete_favorite(self, alias: str) -> bool:
        alias_cf = alias.strip().casefold()
        data = self._read()
        favorites = data["favorites"]

        new_items = [f for f in favorites if (f.get("alias") or "").casefold() != alias_cf]
        changed = len(new_items) != len(favorites)

        if changed:
            data["favorites"] = new_items
            self._write(data)

        return changed
