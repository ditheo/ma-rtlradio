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
        return await 
