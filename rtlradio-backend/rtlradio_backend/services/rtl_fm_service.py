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
        self._cleanup_task: Optional[asyncio.Task] = None

    def _serial_args(self):
        return ["-d", self.serial] if self.serial else []

    async def _stop_active(self, reason: str):
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

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
            LOGGER.warning("[%s] acquiring device for freq=%s", request_id, frequency)

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
            LOGGER.warning("[%s] stream started", request_id)

        async def log_stderr(prefix: str, proc: asyncio.subprocess.Process):
            try:
                while True:
                    line = await proc.stderr.readline()
                    if not line:
                        break
                    LOGGER.warning("[%s] %s stderr: %s", request_id, prefix, line.decode(errors="ignore").rstrip())
            except asyncio.CancelledError:
                raise
            except Exception as err:
                LOGGER.exception("[%s] %s stderr logger error: %s", request_id, prefix, err)

        async def pump():
            try:
                while True:
                    chunk = await rtl.stdout.read(4096)
                    if not chunk:
                        LOGGER.warning("[%s] rtl stdout EOF", request_id)
                        break

                    if ffmpeg.stdin is None:
                        LOGGER.warning("[%s] ffmpeg stdin is None", request_id)
                        break

                    ffmpeg.stdin.write(chunk)
                    await ffmpeg.stdin.drain()
                    await asyncio.sleep(0)
            except (BrokenPipeError, ConnectionResetError) as err:
                LOGGER.warning("[%s] pump pipe closed: %s", request_id, err)
            except asyncio.CancelledError:
                LOGGER.warning("[%s] pump cancelled", request_id)
                raise
            except Exception as err:
                LOGGER.exception("[%s] pump error: %s", request_id, err)
            finally:
                try:
                    if ffmpeg.stdin is not None:
                        ffmpeg.stdin.close()
                except Exception:
                    pass

        rtl_stderr_task = asyncio.create_task(log_stderr("rtl_fm", rtl))
        ffmpeg_stderr_task = asyncio.create_task(log_stderr("ffmpeg", ffmpeg))
        pump_task = asyncio.create_task(pump())

        try:
            while True:
                out = await ffmpeg.stdout.read(4096)
                if not out:
                    LOGGER.warning("[%s] ffmpeg stdout EOF", request_id)
                    break
                yield out
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            LOGGER.warning("[%s] stream cancelled", request_id)
            raise
        except Exception as err:
            LOGGER.exception("[%s] stream loop error: %s", request_id, err)
            raise
        finally:
            LOGGER.warning("[%s] stream cleanup start", request_id)

            for task in (pump_task, rtl_stderr_task, ffmpeg_stderr_task):
                task.cancel()

            async with self._lock:
                if self._active_id == request_id:
                    await self._stop_active("stream_cleanup")

            await asyncio.gather(
                pump_task,
                rtl_stderr_task,
                ffmpeg_stderr_task,
                return_exceptions=True,
            )
            await asyncio.gather(
                rtl.wait(),
                ffmpeg.wait(),
                return_exceptions=True,
            )

            LOGGER.warning("[%s] stream cleanup end", request_id)
