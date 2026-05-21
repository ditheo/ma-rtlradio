from __future__ import annotations

from typing import Any

import httpx


class RadioBrowserService:
    def __init__(self) -> None:
        self._base = "https://de1.api.radio-browser.info/json"
        self._headers = {"User-Agent": "rtlradio-backend/0.3.0"}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=20.0, headers=self._headers) as client:
            resp = await client.get(f"{self._base}{path}", params=params or {})
            resp.raise_for_status()
            return resp.json()

    async def countries(self) -> list[dict[str, Any]]:
        data = await self._get("/countries")
        out = []
        for item in data:
            code = (item.get("iso_3166_1") or item.get("countrycode") or "").strip().upper()
            name = (item.get("name") or item.get("country") or "").strip()
            if not code or not name:
                continue
            out.append(
                {
                    "code": code,
                    "name": name,
                    "stationcount": item.get("stationcount", 0),
                    "favicon": item.get("favicon"),
                }
            )
        out.sort(key=lambda x: (x["name"].lower(), x["code"]))
        return out

    async def states(self, countrycode: str) -> list[dict[str, Any]]:
        params = {
            "countrycode": countrycode.upper(),
            "hidebroken": "true",
        }
        data = await self._get("/states", params=params)
        out = []
        for item in data:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            out.append(
                {
                    "name": name,
                    "stationcount": item.get("stationcount", 0),
                    "countrycode": countrycode.upper(),
                    "favicon": item.get("favicon"),
                }
            )
        out.sort(key=lambda x: x["name"].lower())
        return out

    async def stations(
        self,
        countrycode: str | None = None,
        state: str | None = None,
        name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "hidebroken": "true",
            "order": "name",
            "reverse": "false",
            "limit": max(1, min(limit, 200)),
        }
        if countrycode:
            params["countrycode"] = countrycode.upper()
        if state:
            params["state"] = state
        if name:
            params["name"] = name

        data = await self._get("/stations/search", params=params)
        out = []
        for item in data:
            stationuuid = (item.get("stationuuid") or "").strip()
            station_name = (item.get("name") or "").strip()
            if not stationuuid or not station_name:
                continue

            out.append(
                {
                    "stationuuid": stationuuid,
                    "name": station_name,
                    "countrycode": (item.get("countrycode") or "").strip().upper(),
                    "country": (item.get("country") or "").strip(),
                    "state": (item.get("state") or "").strip(),
                    "language": (item.get("language") or "").strip(),
                    "tags": (item.get("tags") or "").strip(),
                    "codec": (item.get("codec") or "").strip(),
                    "bitrate": item.get("bitrate"),
                    "homepage": item.get("homepage"),
                    "favicon": item.get("favicon"),
                    "url": item.get("url"),
                    "url_resolved": item.get("url_resolved"),
                }
            )
        return out
