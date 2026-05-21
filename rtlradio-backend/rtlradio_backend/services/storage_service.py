import asyncio
import json
import os
from copy import deepcopy
from datetime import datetime, timezone


class StorageService:
    def __init__(self, path: str = "/data/stations.json"):
        self.path = path
        self._lock = asyncio.Lock()

    def _utcnow(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _default_data(self) -> dict:
        return {
            "schema_version": 2,
            "updated_at": self._utcnow(),
            "dab": [],
            "fm": [],
            "favorites": [],
        }

    async def _ensure_file(self):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(self.path):
            async with self._lock:
                if not os.path.exists(self.path):
                    with open(self.path, "w", encoding="utf-8") as f:
                        json.dump(self._default_data(), f, ensure_ascii=False, indent=2)

    async def read(self) -> dict:
        await self._ensure_file()
        async with self._lock:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

        data.setdefault("schema_version", 2)
        data.setdefault("updated_at", self._utcnow())
        data.setdefault("dab", [])
        data.setdefault("fm", [])
        data.setdefault("favorites", [])
        return data

    async def write(self, data: dict) -> dict:
        await self._ensure_file()
        payload = deepcopy(data)
        payload["updated_at"] = self._utcnow()
        payload.setdefault("schema_version", 2)
        payload.setdefault("dab", [])
        payload.setdefault("fm", [])
        payload.setdefault("favorites", [])

        async with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

        return payload

    async def get_all_stations(self) -> dict:
        return await self.read()

    async def get_dab_stations(self) -> list:
        data = await self.read()
        return data.get("dab", [])

    async def get_fm_stations(self) -> list:
        data = await self.read()
        return data.get("fm", [])

    async def get_favorites(self) -> list:
        data = await self.read()
        return data.get("favorites", [])

    async def upsert_dab_stations(self, stations: list) -> dict:
        data = await self.read()
        current = data.get("dab", [])
        by_id = {item["id"]: item for item in current if "id" in item}

        for station in stations:
            by_id[station["id"]] = station

        data["dab"] = sorted(
            by_id.values(),
            key=lambda x: (
                x.get("block", ""),
                (x.get("name") or "").lower(),
                x.get("sid", ""),
            ),
        )
        return await self.write(data)

    async def add_fm_station(self, name: str, frequency: float) -> dict:
        data = await self.read()
        freq = round(float(frequency), 1)
        station_id = f"fm:{freq:.1f}"

        station = {
            "id": station_id,
            "type": "fm",
            "name": name,
            "frequency": freq,
            "stream_path": f"/stream/fm/{freq}",
            "last_seen": self._utcnow(),
        }

        current = data.get("fm", [])
        by_id = {item["id"]: item for item in current if "id" in item}
        by_id[station_id] = station

        data["fm"] = sorted(
            by_id.values(),
            key=lambda x: (x.get("frequency", 0), (x.get("name") or "").lower()),
        )
        return await self.write(data)

    async def delete_station(self, station_id: str) -> dict:
        data = await self.read()
        data["dab"] = [item for item in data.get("dab", []) if item.get("id") != station_id]
        data["fm"] = [item for item in data.get("fm", []) if item.get("id") != station_id]
        return await self.write(data)

    async def get_station(self, station_id: str):
        data = await self.read()
        for item in data.get("dab", []):
            if item.get("id") == station_id:
                return item
        for item in data.get("fm", []):
            if item.get("id") == station_id:
                return item
        return None

    async def get_station_target(self, station_id: str):
        station = await self.get_station(station_id)
        if not station:
            return None

        stype = station.get("type")
        if stype == "dab":
            return {
                "type": "dab",
                "station_id": station.get("id"),
                "target_path": f"/dab/play/{station.get('id')}",
                "name": station.get("name"),
            }

        if stype == "fm":
            freq = station.get("frequency")
            return {
                "type": "fm",
                "station_id": station.get("id"),
                "target_path": f"/stream/fm/{freq}",
                "name": station.get("name"),
            }

        return None

    async def upsert_favorite(self, alias: str, station_id: str) -> dict:
        data = await self.read()

        alias_clean = alias.strip()
        if not alias_clean:
            raise ValueError("alias is required")

        target = await self.get_station_target(station_id)
        if not target:
            raise ValueError(f"station not found: {station_id}")

        favorite = {
            "alias": alias_clean,
            "alias_key": alias_clean.casefold(),
            "station_id": target["station_id"],
            "station_type": target["type"],
            "target_path": target["target_path"],
            "source_name": target.get("name"),
            "updated_at": self._utcnow(),
        }

        favorites = data.get("favorites", [])
        by_alias = {
            item.get("alias_key", (item.get("alias") or "").casefold()): item
            for item in favorites
            if item.get("alias") or item.get("alias_key")
        }
        by_alias[favorite["alias_key"]] = favorite

        data["favorites"] = sorted(
            by_alias.values(),
            key=lambda x: (x.get("alias") or "").casefold(),
        )
        return await self.write(data)

    async def delete_favorite(self, alias: str) -> dict:
        data = await self.read()
        wanted = alias.strip().casefold()
        data["favorites"] = [
            item for item in data.get("favorites", [])
            if (item.get("alias_key") or (item.get("alias") or "").casefold()) != wanted
        ]
        return await self.write(data)

    async def get_favorite(self, alias: str):
        data = await self.read()
        wanted = alias.strip().casefold()
        for item in data.get("favorites", []):
            alias_key = item.get("alias_key") or (item.get("alias") or "").casefold()
            if alias_key == wanted:
                return item
        return None
