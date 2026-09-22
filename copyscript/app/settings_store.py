from __future__ import annotations

import json
import logging
import os
import tempfile
from json import JSONDecodeError
from pathlib import Path

from copyscript.config.constants import DEFAULT_CACHE_MAX_ITEMS, MAX_HISTORY_ITEMS
from copyscript.config.languages import SUPPORTED_LANGUAGES
from copyscript.config.models import AppSettings, HistoryEntry
from copyscript.platform.app_paths import get_settings_path

logger = logging.getLogger(__name__)
SUPPORTED_LANGUAGE_CODES = {code for _, code in SUPPORTED_LANGUAGES}


class SettingsStore:
    def __init__(self) -> None:
        self.settings_path = get_settings_path()

    def load(self) -> AppSettings:
        settings = AppSettings()
        try:
            if self.settings_path.exists():
                loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    settings.lang_code = self._sanitize_language_code(
                        loaded.get("lang_code"), settings.lang_code
                    )
                    settings.include_timestamp = self._sanitize_bool(
                        loaded.get("include_timestamp"), settings.include_timestamp
                    )
                    settings.monitor_on_launch = self._load_monitor_on_launch(
                        loaded, settings
                    )
                    settings.launch_at_login = self._sanitize_bool(
                        loaded.get("launch_at_login"), settings.launch_at_login
                    )
                    settings.window_geometry = self._sanitize_string(
                        loaded.get("window_geometry"), settings.window_geometry
                    )
                    settings.cache_max_items = self._sanitize_cache_size(
                        loaded.get("cache_max_items")
                    )
                    settings.recent_history = self._sanitize_history(
                        loaded.get("recent_history")
                    )
        except (OSError, JSONDecodeError, UnicodeDecodeError):
            logger.warning(
                "Failed to load settings from %s", self.settings_path, exc_info=True
            )
            return settings
        return settings

    def save(self, settings: AppSettings) -> None:
        payload = settings.to_dict()
        try:
            self._write_atomic(json.dumps(payload, ensure_ascii=False, indent=2))
        except OSError:
            logger.warning(
                "Failed to save settings to %s", self.settings_path, exc_info=True
            )

    def _write_atomic(self, text: str) -> None:
        # 같은 디렉터리의 임시 파일에 모두 기록한 뒤 교체한다.
        # 저장 중 종료되거나 쓰기가 겹쳐도 settings.json이 잘리지 않는다.
        fd, tmp_name = tempfile.mkstemp(
            dir=self.settings_path.parent,
            prefix=".settings-",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            if self.settings_path.exists():
                os.chmod(tmp_path, self.settings_path.stat().st_mode & 0o777)
            os.replace(tmp_path, self.settings_path)
        except BaseException:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _sanitize_history(self, history_data: object) -> list[HistoryEntry]:
        if not isinstance(history_data, list):
            return []
        sanitized: list[HistoryEntry] = []
        for item in history_data[:MAX_HISTORY_ITEMS]:
            entry = HistoryEntry.from_dict(item)
            if entry is not None:
                sanitized.append(entry)
        return sanitized

    def _sanitize_cache_size(self, value: object) -> int:
        if not isinstance(value, int | str):
            return DEFAULT_CACHE_MAX_ITEMS
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return DEFAULT_CACHE_MAX_ITEMS

    def _load_monitor_on_launch(
        self, loaded: dict[object, object], settings: AppSettings
    ) -> bool:
        if "monitor_on_launch" in loaded:
            return self._sanitize_bool(
                loaded.get("monitor_on_launch"), settings.monitor_on_launch
            )
        return self._sanitize_bool(loaded.get("auto_start"), settings.monitor_on_launch)

    def _sanitize_bool(self, value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return default

    def _sanitize_language_code(self, value: object, default: str) -> str:
        if isinstance(value, str) and value in SUPPORTED_LANGUAGE_CODES:
            return value
        return default

    def _sanitize_string(self, value: object, default: str) -> str:
        if isinstance(value, str):
            return value
        return default
