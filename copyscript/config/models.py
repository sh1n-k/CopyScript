from __future__ import annotations

from dataclasses import dataclass, field

from copyscript.config.constants import DEFAULT_CACHE_MAX_ITEMS, DEFAULT_LANG_CODE


@dataclass(frozen=True)
class ProcessingOptions:
    lang_code: str = DEFAULT_LANG_CODE
    include_timestamp: bool = False


@dataclass(frozen=True)
class HistoryEntry:
    time: str
    status: str
    video_id: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "time": self.time,
            "status": self.status,
            "video_id": self.video_id,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry | None":
        if not isinstance(data, dict):
            return None
        return cls(
            time=str(data.get("time", "")),
            status=str(data.get("status", "")),
            video_id=str(data.get("video_id", "")),
            detail=str(data.get("detail", "")),
        )


@dataclass
class AppSettings:
    lang_code: str = DEFAULT_LANG_CODE
    include_timestamp: bool = False
    auto_start: bool = True
    cache_max_items: int = DEFAULT_CACHE_MAX_ITEMS
    window_geometry: str = ""
    recent_history: list[HistoryEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lang_code": self.lang_code,
            "include_timestamp": self.include_timestamp,
            "auto_start": self.auto_start,
            "cache_max_items": self.cache_max_items,
            "window_geometry": self.window_geometry,
            "recent_history": [item.to_dict() for item in self.recent_history],
        }
