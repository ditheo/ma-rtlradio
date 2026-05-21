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
            "schema_version": 1,
            "updated_at": self._utcnow(),
            "dab": [],
            "fm": [],
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
        data.setdefault("schema_version", 1)
        data.setdefault("updated_at", self._utcnow())
        data.setdefault("dab", [])
        data.setdefault("fm", [])
        return data

    async def write(self, data: dict) -> dict:
        await self._ensure_file()
        payload = deepcopy(data)
        payload["updated_at"] = self._utcnow()
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
        station_id = f"fm:{frequency:.1f}"

        station = {
            "id": station_id,
            "type": "fm",
            "name": name,
            "frequency": round(float(frequency), 1),
            "stream_path": f"/stream/fm/{round(float(frequency), 1)}",
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
