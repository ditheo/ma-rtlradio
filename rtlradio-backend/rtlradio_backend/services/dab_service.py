import asyncio
import logging

LOGGER = logging.getLogger(__name__)


class DabService:
    async def info(self) -> dict:
        proc = await asyncio.create_subprocess_exec(
            'welle-cli', '--help',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            'installed': proc.returncode == 0,
            'returncode': proc.returncode,
            'stdout': stdout.decode(errors='ignore')[:4000],
            'stderr': stderr.decode(errors='ignore')[:4000],
        }

    async def scan(self, block: str) -> dict:
        """Proof-of-concept: run welle-cli against a DAB block.
        This is intentionally conservative until we verify runtime behavior in the add-on.
        """
        cmd = [
            'welle-cli',
            '--rtl-sdr',
            '--channel', block,
            '--scan',
        ]
        LOGGER.warning('DAB scan cmd=%s', cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
        except asyncio.TimeoutError:
            proc.terminate()
            await asyncio.gather(proc.wait(), return_exceptions=True)
            return {
                'block': block,
                'status': 'timeout',
                'message': 'welle-cli scan timed out after 20 seconds',
            }
        return {
            'block': block,
            'returncode': proc.returncode,
            'stdout': stdout.decode(errors='ignore')[:8000],
            'stderr': stderr.decode(errors='ignore')[:8000],
        }
