"""자막 텍스트 로컬 캐시 (설정 분리 + LRU)"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Optional

from app_paths import get_cache_index_path, get_cache_items_dir


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cache_key(video_id: str, lang_code: str, include_timestamp: bool) -> str:
    return f"{video_id}|{lang_code}|{1 if include_timestamp else 0}"


@dataclass
class CacheEntry:
    key: str
    video_id: str
    lang_code: str
    include_timestamp: bool
    file_name: str
    line_count: int
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "video_id": self.video_id,
            "lang_code": self.lang_code,
            "include_timestamp": self.include_timestamp,
            "file_name": self.file_name,
            "line_count": self.line_count,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional["CacheEntry"]:
        try:
            key = str(data.get("key", ""))
            video_id = str(data.get("video_id", ""))
            lang_code = str(data.get("lang_code", ""))
            file_name = str(data.get("file_name", ""))
            if not key or not video_id or not lang_code or not file_name:
                return None
            return cls(
                key=key,
                video_id=video_id,
                lang_code=lang_code,
                include_timestamp=bool(data.get("include_timestamp", False)),
                file_name=file_name,
                line_count=max(0, int(data.get("line_count", 0))),
                updated_at=str(data.get("updated_at", "")),
            )
        except Exception:
            return None


class SubtitleCache:
    """설정 조합(video/lang/timestamp) 기준 텍스트 캐시"""

    def __init__(
        self,
        max_items: int = 100,
        index_path: Optional[Path] = None,
        items_dir: Optional[Path] = None,
    ):
        self.max_items = max(1, int(max_items))
        self.index_path = index_path or get_cache_index_path()
        self.items_dir = items_dir or get_cache_items_dir()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.items_dir.mkdir(parents=True, exist_ok=True)
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._load()

    def _load(self) -> None:
        self._entries.clear()
        if not self.index_path.exists():
            return
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            entries = data.get("entries", [])
            if not isinstance(entries, list):
                return
            for raw in entries:
                if not isinstance(raw, dict):
                    continue
                entry = CacheEntry.from_dict(raw)
                if entry is None:
                    continue
                self._entries[entry.key] = entry
            self._evict_if_needed(save=False)
        except Exception:
            self._entries.clear()

    def _save(self) -> None:
        payload = {
            "max_items": self.max_items,
            "entries": [entry.to_dict() for entry in self._entries.values()],
        }
        self.index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def set_max_items(self, max_items: int) -> None:
        self.max_items = max(1, int(max_items))
        self._evict_if_needed(save=True)

    def clear_all(self) -> None:
        for entry in list(self._entries.values()):
            path = self.items_dir / entry.file_name
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
        self._entries.clear()
        self._save()

    def _entry_file_name(self, key: str) -> str:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return f"{digest}.txt"

    def get(self, video_id: str, lang_code: str, include_timestamp: bool) -> Optional[str]:
        key = _cache_key(video_id, lang_code, include_timestamp)
        entry = self._entries.get(key)
        if entry is None:
            return None

        path = self.items_dir / entry.file_name
        if not path.exists():
            self._entries.pop(key, None)
            self._save()
            return None

        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return None

        entry.updated_at = _utc_now_iso()
        self._entries.move_to_end(key)
        self._save()
        return text

    def put(self, video_id: str, lang_code: str, include_timestamp: bool, text: str) -> None:
        key = _cache_key(video_id, lang_code, include_timestamp)
        now = _utc_now_iso()
        file_name = self._entry_file_name(key)
        path = self.items_dir / file_name
        path.write_text(text, encoding="utf-8")

        line_count = text.count("\n") + 1 if text else 0
        entry = CacheEntry(
            key=key,
            video_id=video_id,
            lang_code=lang_code,
            include_timestamp=include_timestamp,
            file_name=file_name,
            line_count=line_count,
            updated_at=now,
        )
        self._entries[key] = entry
        self._entries.move_to_end(key)
        self._evict_if_needed(save=True)

    def _evict_if_needed(self, save: bool) -> None:
        changed = False
        while len(self._entries) > self.max_items:
            _, oldest = self._entries.popitem(last=False)
            path = self.items_dir / oldest.file_name
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
            changed = True
        if save or changed:
            self._save()

    def stats(self) -> dict:
        """캐시 상태 요약 반환 (UI 표시용)."""
        total_chars = 0
        total_lines = 0
        total_bytes = 0
        entries_recent = []

        for entry in self._entries.values():
            path = self.items_dir / entry.file_name
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    total_chars += len(content)
                    total_lines += content.count("\n") + 1 if content else 0
                    total_bytes += path.stat().st_size
                except Exception:
                    continue
            entries_recent.append(
                {
                    "video_id": entry.video_id,
                    "lang_code": entry.lang_code,
                    "include_timestamp": entry.include_timestamp,
                    "line_count": entry.line_count,
                    "updated_at": entry.updated_at,
                }
            )

        item_count = len(entries_recent)
        max_items = max(1, self.max_items)
        utilization = int((item_count / max_items) * 100)
        return {
            "item_count": item_count,
            "max_items": max_items,
            "utilization_pct": utilization,
            "total_chars": total_chars,
            "total_lines": total_lines,
            "total_bytes": total_bytes,
            # 최신 항목이 먼저 보이도록 reverse
            "entries_recent": list(reversed(entries_recent)),
        }
