import asyncio
from contextlib import suppress

import aiohttp


class DabService:
    def __init__(self):
        self._proc = None
        self._block = None
        self._port = None

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

    async def scan(self, block: str):
        block = block.upper()
        cmd = ["welle-cli", "-c", block, "-D"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=25)

            return {
                "block": block,
                "returncode": proc.returncode,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "cmd": cmd,
            }
        except FileNotFoundError:
            return {
                "block": block,
                "returncode": None,
                "stdout": "",
                "stderr": "welle-cli not found",
                "cmd": cmd,
            }
        except asyncio.TimeoutError:
            with suppress(Exception):
                proc.kill()
            return {
                "block": block,
                "returncode": None,
                "stdout": "",
                "stderr": "scan timeout",
                "cmd": cmd,
            }
        except Exception as exc:
            return {
                "block": block,
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

    async def status(self):
        running = self._proc is not None and self._proc.returncode is None
        return {
            "running": running,
            "block": self._block,
            "port": self._port,
            "mux_url": f"http://127.0.0.1:{self._port}/mux.json" if self._port else None,
            "base_url": f"http://127.0.0.1:{self._port}" if self._port else None,
        }

    async def mux(self):
        if not self._port:
            return {
                "running": False,
                "error": "web server not started",
            }

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
