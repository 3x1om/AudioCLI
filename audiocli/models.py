from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Track:
    title: str
    webpage_url: str
    stream_url: str
    source: str
    duration: int | None = None
    repeat: bool = False

    @property
    def pretty_duration(self) -> str:
        if not self.duration:
            return "--:--"
        minutes, seconds = divmod(self.duration, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
