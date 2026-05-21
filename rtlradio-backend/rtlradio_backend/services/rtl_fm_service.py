import asyncio
import os
from typing import AsyncGenerator


class RtlFmService:
    def __init__(self):
        self.serial = os.environ.get("DEVICE_SERIAL", "")

    def _serial_args(self):
        return ["-d", self.serial] if self.serial else []

    async def stream(self, frequency: float) -> AsyncGenerator[bytes, None]:
        freq_hz = int(frequency * 1_000_000)
        rtl_cmd = [
            "rtl_fm", "-f", str(freq_hz), "-M", "wbfm",
            "-s", "200000", "-r", "44100", "-"
        ] + self._serial_args()
        ffmpeg_cmd = [
            "ffmpeg", "-loglevel", "quiet",
            "-f", "s16le", "-ar", "44100", "-ac", "1", "-i", "pipe:0",
            "-acodec", "libmp3lame", "-b:a", "128k", "-ac", "2",
            "-f", "mp3", "pipe:1",
        ]

        rtl = await asyncio.create_subprocess_exec(
            *rtl_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        ffmpeg = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        async def pump():
            try:
                while True:
                    chunk = await rtl.stdout.read(4096)
                    if not chunk:
                        break
                    ffmpeg.stdin.write(chunk)
                    await ffmpeg.stdin.drain()
            finally:
                try:
                    ffmpeg.stdin.close()
                except Exception:
                    pass

        pump_task = asyncio.create_task(pump())

        try:
            while True:
                out = await ffmpeg.stdout.read(4096)
                if not out:
                    break
                yield out
        finally:
            pump_task.cancel()
            for proc in (rtl, ffmpeg):
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
            await asyncio.gather(pump_task, return_exceptions=True)
            await asyncio.gather(rtl.wait(), ffmpeg.wait(), return_exceptions=True)
