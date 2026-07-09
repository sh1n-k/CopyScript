from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from copyscript.config.constants import DEFAULT_CACHE_MAX_ITEMS, DEFAULT_LANG_CODE


class HistoryEntryDict(TypedDict):
    time: str
    status: str
    video_id: str
    detail: str


class AppSettingsDict(TypedDict):
    lang_code: str
    include_timestamp: bool
    monitor_on_launch: bool
    launch_at_login: bool
    cache_max_items: int
    window_geometry: str
    recent_history: list[HistoryEntryDict]


class CacheEntryDict(TypedDict):
    video_id: str
    lang_code: str
    include_timestamp: bool
    line_count: int
    updated_at: str


class CacheStatsDict(TypedDict):
    item_count: int
    max_items: int
    utilization_pct: int
    total_chars: int
    total_lines: int
    total_bytes: int
    entries_recent: list[CacheEntryDict]


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

    def to_dict(self) -> HistoryEntryDict:
        return {
            "time": self.time,
            "status": self.status,
            "video_id": self.video_id,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: object) -> HistoryEntry | None:
        if not isinstance(data, dict):
            return None
        raw = data
        return cls(
            time=str(raw.get("time", "")),
            status=str(raw.get("status", "")),
            video_id=str(raw.get("video_id", "")),
            detail=str(raw.get("detail", "")),
        )


@dataclass
class AppSettings:
    lang_code: str = DEFAULT_LANG_CODE
    include_timestamp: bool = False
    monitor_on_launch: bool = True
    launch_at_login: bool = True
    cache_max_items: int = DEFAULT_CACHE_MAX_ITEMS
    window_geometry: str = ""
    recent_history: list[HistoryEntry] = field(default_factory=list)

    def to_dict(self) -> AppSettingsDict:
        return {
            "lang_code": self.lang_code,
            "include_timestamp": self.include_timestamp,
            "monitor_on_launch": self.monitor_on_launch,
            "launch_at_login": self.launch_at_login,
            "cache_max_items": self.cache_max_items,
            "window_geometry": self.window_geometry,
            "recent_history": [item.to_dict() for item in self.recent_history],
        }
