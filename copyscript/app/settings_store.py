from __future__ import annotations

import json
import os
import tempfile

from copyscript.config.constants import DEFAULT_CACHE_MAX_ITEMS, MAX_HISTORY_ITEMS
from copyscript.config.models import AppSettings, HistoryEntry
from copyscript.platform.app_paths import get_settings_path


class SettingsStore:
    def __init__(self):
        self.settings_path = get_settings_path()

    def load(self) -> AppSettings:
        settings = AppSettings()
        if not self.settings_path.exists():
            return settings
        try:
            loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            # 손상된 설정 파일은 조용히 버리지 않고 .bak으로 보존해
            # 사용자 설정/기록이 복구 가능하도록 남긴다.
            self._preserve_corrupt_file()
            return settings
        try:
            if isinstance(loaded, dict):
                settings.lang_code = str(loaded.get("lang_code", settings.lang_code))
                settings.include_timestamp = bool(loaded.get("include_timestamp", settings.include_timestamp))
                settings.monitor_on_launch = self._load_monitor_on_launch(loaded, settings)
                settings.launch_at_login = bool(loaded.get("launch_at_login", settings.launch_at_login))
                settings.window_geometry = str(loaded.get("window_geometry", settings.window_geometry))
                settings.cache_max_items = self._sanitize_cache_size(loaded.get("cache_max_items"))
                settings.recent_history = self._sanitize_history(loaded.get("recent_history"))
        except Exception:
            return settings
        return settings

    def save(self, settings: AppSettings) -> None:
        payload = settings.to_dict()
        try:
            text = json.dumps(payload, ensure_ascii=False, indent=2)
            directory = self.settings_path.parent
            # 임시 파일에 먼저 기록한 뒤 os.replace로 원자적으로 교체한다.
            # 중간에 종료되거나 동시 저장이 일어나도 기존 파일이 잘리거나
            # 깨지지 않는다.
            fd, tmp_name = tempfile.mkstemp(dir=str(directory), prefix=".settings-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(text)
                os.replace(tmp_name, self.settings_path)
            except Exception:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise
        except Exception:
            pass

    def _preserve_corrupt_file(self) -> None:
        try:
            backup = self.settings_path.with_name(self.settings_path.name + ".bak")
            os.replace(self.settings_path, backup)
        except OSError:
            pass

    def _sanitize_history(self, history_data) -> list[HistoryEntry]:
        if not isinstance(history_data, list):
            return []
        sanitized: list[HistoryEntry] = []
        for item in history_data[:MAX_HISTORY_ITEMS]:
            entry = HistoryEntry.from_dict(item)
            if entry is not None:
                sanitized.append(entry)
        return sanitized

    def _sanitize_cache_size(self, value) -> int:
        try:
            return max(1, int(value))
        except Exception:
            return DEFAULT_CACHE_MAX_ITEMS

    def _load_monitor_on_launch(self, loaded: dict, settings: AppSettings) -> bool:
        if "monitor_on_launch" in loaded:
            return bool(loaded.get("monitor_on_launch", settings.monitor_on_launch))
        return bool(loaded.get("auto_start", settings.monitor_on_launch))
