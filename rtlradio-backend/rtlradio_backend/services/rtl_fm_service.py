import asyncio, os
from typing import AsyncGenerator

class RtlFmService:
    def __init__(self):
        self.serial = os.environ.get("DEVICE_SERIAL", "")

    def _serial_args(self):
        return ["-d", self.serial] if self.serial else []

    async def tune(self, frequency: float):
        """Tune RTL-SDR to frequency (MHz) — no audio output."""
        freq_hz = int(frequency * 1_000_000)
        args = ["rtl_fm", "-f", str(freq_hz), "-M", "wbfm",
                "-s", "200000", "-"] + self._serial_args()
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.sleep(1)
        proc.terminate()

    async def stream(self, frequency: float) -> AsyncGenerator[bytes, None]:
        """Yield MP3 audio bytes from the given FM frequency."""
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
        rtl = await asyncio.create_subprocess_exec(
            *rtl_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        ffmpeg = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=rtl.stdout,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            while True:
                chunk = await ffmpeg.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        finally:
            rtl.terminate()
            ffmpeg.terminate()
