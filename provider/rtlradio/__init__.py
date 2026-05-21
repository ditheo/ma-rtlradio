"""RTL-SDR Radio provider for Music Assistant."""
from __future__ import annotations
import json
from music_assistant.models.media_items import Radio
from music_assistant.models.provider import MusicProvider
from music_assistant.models.streamdetails import StreamDetails, StreamType

DOMAIN = "rtlradio"

class RTLRadioProvider(MusicProvider):
    domain = DOMAIN

    async def setup(self) -> None:
        self._backend = self.config.get_value("backend_url")
        raw = self.config.get_value("stations")
        self._stations = json.loads(raw)

    async def get_library_radios(self):
        for s in self._stations:
            item = Radio()
            item.item_id = str(s["frequency"])
            item.name = s["name"]
            item.provider = self.domain
            yield item

    async def get_stream_details(self, item_id: str) -> StreamDetails:
        freq = float(item_id)
        return StreamDetails(
            type=StreamType.HTTP,
            item_id=item_id,
            provider=self.domain,
            path=f"{self._backend}/fm/stream/{freq}",
            mime_type="audio/mpeg",
        )
