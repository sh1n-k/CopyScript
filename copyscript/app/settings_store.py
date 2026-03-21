from __future__ import annotations

import json

from copyscript.config.constants import DEFAULT_CACHE_MAX_ITEMS, MAX_HISTORY_ITEMS
from copyscript.config.models import AppSettings, HistoryEntry
from copyscript.platform.app_paths import get_settings_path


class SettingsStore:
    def __init__(self):
        self.settings_path = get_settings_path()

    def load(self) -> AppSettings:
        settings = AppSettings()
        try:
            if self.settings_path.exists():
                loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
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
            self.settings_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
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
