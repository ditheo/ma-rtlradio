import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

import aiohttp

from . import radio_state


class DabService:
    def __init__(self):
        self._proc = None
        self._block = None
        self._port = None
        self._default_block = "5A"

    def _utcnow(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def info(self):
        cmd = ["welle-cli", "-h"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            return {
                "installed": True,
                "returncode": proc.returncode,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "cmd": cmd,
            }
        except FileNotFoundError:
            return {
                "installed": False,
                "returncode": None,
                "stdout": "",
                "stderr": "welle-cli not found",
                "cmd": cmd,
            }
        except Exception as exc:
            return {
                "installed": False,
                "returncode": None,
                "stdout": "",
                "stderr": str(exc),
                "cmd": cmd,
            }

    async def stop(self):
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._proc.kill()
                await self._proc.wait()

        self._proc = None
        self._block = None
        self._port = None
        return {"running": False}

    async def start_web(self, block: str, port: int = 7979):
        block = block.upper()

        if self._proc and self._proc.returncode is None:
            if self._block == block and self._port == port:
                return {
                    "running": True,
                    "block": self._block,
                    "port": self._port,
                    "mux_url": f"http://127.0.0.1:{self._port}/mux.json",
                    "base_url": f"http://127.0.0.1:{self._port}",
                }
            await self.stop()

        cmd = ["welle-cli", "-c", block, "-w", str(port)]

        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._block = block
        self._port = port

        for _ in range(20):
            if self._proc.returncode is not None:
                stderr = ""
                if self._proc.stderr:
                    try:
                        stderr = (await self._proc.stderr.read()).decode(errors="replace")
                    except Exception:
                        pass
                raise RuntimeError(f"welle-cli exited early: {stderr}")

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://127.0.0.1:{port}/mux.json", timeout=2) as resp:
                        if resp.status == 200:
                            return {
                                "running": True,
                                "block": block,
                                "port": port,
                                "mux_url": f"http://127.0.0.1:{port}/mux.json",
                                "base_url": f"http://127.0.0.1:{port}",
                                "cmd": cmd,
                            }
            except Exception:
                await asyncio.sleep(1)

        return {
            "running": True,
            "block": block,
            "port": port,
            "mux_url": f"http://127.0.0.1:{port}/mux.json",
            "base_url": f"http://127.0.0.1:{port}",
            "cmd": cmd,
            "warning": "web server started but mux.json not reachable yet",
        }

    async def ensure_block_running(self, block: str, port: int = 7979):
        async with radio_state.radio_lock:
            if radio_state.fm_service is not None:
                await radio_state.fm_service.stop()
            result = await self.start_web(block, port)
            radio_state.active_mode = "dab"
            return result

    async def mux(self):
        if not self._port:
            return {"running": False, "error": "web server not started"}

        url = f"http://127.0.0.1:{self._port}/mux.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                text = await resp.text()
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = None

                return {
                    "running": True,
                    "block": self._block,
                    "port": self._port,
                    "url": url,
                    "status_code": resp.status,
                    "json": data,
                    "raw": text,
                }

    async def scan_and_store(self, block: str):
        block = block.upper()
        await self.ensure_block_running(block, 7979)
        mux_data = await self.mux()
        payload = mux_data.get("json") or {}
        ensemble = ((payload.get("ensemble") or {}).get("label") or {}).get("label")
        services = payload.get("services") or []

        stations = []
        for svc in services:
            sid = svc.get("sid")
            label = ((svc.get("label") or {}).get("label")) or sid
            shortlabel = ((svc.get("label") or {}).get("shortlabel")) or label
            pty = svc.get("ptystring")
            url_mp3 = svc.get("url_mp3")
            subchannels = svc.get("subchannels") or []
            bitrate = None
            if subchannels and isinstance(subchannels[0], dict):
                bitrate = subchannels[0].get("bitrate")

            if sid:
                stations.append({
                    "id": f"dab:{block}:{sid}",
                    "type": "dab",
                    "name": label,
                    "short_name": shortlabel,
                    "sid": sid,
                    "block": block,
                    "ensemble": ensemble,
                    "genre": pty,
                    "bitrate": bitrate,
                    "url_mp3": url_mp3,
                    "stream_path": f"/dab/play/dab:{block}:{sid}",
                    "last_seen": self._utcnow(),
                })

        if radio_state.storage_service is None:
            raise RuntimeError("storage service not configured")

        await radio_state.storage_service.upsert_dab_stations(stations)

        return {
            "running": True,
            "block": block,
            "ensemble": ensemble,
            "count": len(stations),
            "stations": stations,
        }

    async def proxy_stream_by_station_id(self, station_id: str):
        if radio_state.storage_service is None:
            raise RuntimeError("storage service not configured")

        station = await radio_state.storage_service.get_station(station_id)
        if not station:
            raise RuntimeError(f"station not found: {station_id}")
        if station.get("type") != "dab":
            raise RuntimeError(f"station is not dab: {station_id}")

        block = (station.get("block") or self._default_block).upper()
        await self.ensure_block_running(block, 7979)

        url_mp3 = station.get("url_mp3")
        if not url_mp3:
            raise RuntimeError(f"station has no url_mp3: {station_id}")

        parsed = urlparse(url_mp3)
        if parsed.scheme or parsed.netloc:
            upstream_url = url_mp3
        elif parsed.path:
            upstream_url = f"http://127.0.0.1:{self._port}{parsed.path}"
            if parsed.query:
                upstream_url += f"?{parsed.query}"
        else:
            raise RuntimeError(f"invalid url_mp3 for station {station_id}: {url_mp3}")

        async def generator():
            session = aiohttp.ClientSession()
            resp = None
            try:
                resp = await session.get(upstream_url, timeout=None)
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"upstream stream failed: {resp.status} url={upstream_url} body={body[:300]}"
                    )
                async for chunk in resp.content.iter_chunked(4096):
                    if chunk:
                        yield chunk
            finally:
                try:
                    if resp is not None:
                        resp.close()
                except Exception:
                    pass
                await session.close()

        return generator()
