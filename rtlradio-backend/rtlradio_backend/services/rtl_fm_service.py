import asyncio
import logging
import os
import uuid
from typing import AsyncGenerator, Optional

LOGGER = logging.getLogger(__name__)


class RtlFmService:
    def __init__(self):
        self.serial = os.environ.get("DEVICE_SERIAL", "")
        self._lock = asyncio.Lock()
        self._active_id: Optional[str] = None
        self._active_rtl: Optional[asyncio.subprocess.Process] = None
        self._active_ffmpeg: Optional[asyncio.subprocess.Process] = None

    def _serial_args(self):
        return ["-d", self.serial] if self.serial else []

    async def _stop_active(self, reason: str):
        for proc_name, proc in (("rtl_fm", self._active_rtl), ("ffmpeg", self._active_ffmpeg)):
            if proc is None:
                continue
            try:
                proc.terminate()
                LOGGER.warning("stop_active reason=%s sent terminate to %s", reason, proc_name)
            except ProcessLookupError:
                LOGGER.warning("stop_active reason=%s %s already exited", reason, proc_name)
            except Exception as err:
                LOGGER.warning("stop_active reason=%s %s terminate error=%s", reason, proc_name, err)

        if self._active_rtl or self._active_ffmpeg:
            await asyncio.gather(
                *(p.wait() for p in (self._active_rtl, self._active_ffmpeg) if p is not None),
                return_exceptions=True,
            )

        self._active_id = None
        self._active_rtl = None
        self._active_ffmpeg = None
        await asyncio.sleep(0.75)

    async def stop(self):
        async with self._lock:
            await self._stop_active("external_stop")
        return {"running": False}

    async def stream(self, frequency: float) -> AsyncGenerator[bytes, None]:
        request_id = uuid.uuid4().hex[:8]
        freq_hz = int(frequency * 1_000_000)

        rtl_cmd = [
            "rtl_fm",
            "-f",
            str(freq_hz),
            "-M",
            "wbfm",
            "-s",
            "200000",
            "-r",
            "44100",
            "-",
        ] + self._serial_args()

        ffmpeg_cmd = [
            "ffmpeg",
            "-loglevel",
            "warning",
            "-f",
            "s16le",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-i",
            "pipe:0",
            "-acodec",
            "libmp3lame",
            "-b:a",
            "128k",
            "-ac",
            "2",
            "-f",
            "mp3",
            "pipe:1",
        ]

        async with self._lock:
            await self._stop_active("new_stream")

            rtl = await asyncio.create_subprocess_exec(
                *rtl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            ffmpeg = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._active_id = request_id
            self._active_rtl = rtl
            self._active_ffmpeg = ffmpeg

        async def pump():
            try:
                while True:
                    chunk = await rtl.stdout.read(4096)
                    if not chunk:
                        break
                    if ffmpeg.stdin is None:
                        break
                    ffmpeg.stdin.write(chunk)
                    await ffmpeg.stdin.drain()
            finally:
                try:
                    if ffmpeg.stdin is not None:
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
            async with self._lock:
                if self._active_id == request_id:
                    await self._stop_active("stream_cleanup")
            await asyncio.gather(pump_task, rtl.wait(), ffmpeg.wait(), return_exceptions=True)
