import asyncio


class DabService:
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
        cmd = ["welle-cli", "-c", block, "-D"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)

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
        except Exception as exc:
            return {
                "block": block,
                "returncode": None,
                "stdout": "",
                "stderr": str(exc),
                "cmd": cmd,
            }
