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

        rtl_cmd = (
            ["rtl_fm", "-f", str(freq_hz), "-M", "wbfm",
             "-s", "200000", "-r", "44100", "-"]
            + self._serial_args()
        )
        ffmpeg_cmd = [
            "ffmpeg", "-loglevel", "quiet",
            "-f", "s16le", "-ar", "44100", "-ac", "1", "-i", "pipe:0",
            "-acodec", "libmp3lame", "-b:a", "128k", "-ac", "2",
            "-f", "mp3", "pipe:1",
        ]

        r_fd, w_fd = os.pipe()

        rtl = await asyncio.create_subprocess_exec(
            *rtl_cmd,
            stdout=w_fd,
            stderr=asyncio.subprocess.DEVNULL,
        )
        os.close(w_fd)

        ffmpeg = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=r_fd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        os.close(r_fd)

        try:
            while True:
                chunk = await ffmpeg.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        finally:
            try:
                rtl.terminate()
            except ProcessLookupError:
                pass
            try:
                ffmpeg.terminate()
            except ProcessLookupError:
                pass
            await asyncio.gather(rtl.wait(), ffmpeg.wait(), return_exceptions=True)
