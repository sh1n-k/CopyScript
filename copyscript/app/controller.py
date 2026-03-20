from __future__ import annotations

from datetime import datetime
from typing import Callable

from copyscript.app.settings_store import SettingsStore
from copyscript.config.models import HistoryEntry, ProcessingOptions
from copyscript.core.clipboard_monitor import ClipboardMonitor
from copyscript.core.subtitle_cache import SubtitleCache
from copyscript.core.subtitle_fetcher import SubtitleFetcher
from copyscript.platform.clipboard_watchers import ClipboardWatcher, create_watcher
from copyscript.platform.notifier import Notifier

StatusHandler = Callable[[str, bool], None]
HistoryHandler = Callable[[list[HistoryEntry]], None]
CacheHandler = Callable[[dict], None]
RunningHandler = Callable[[bool], None]


class AppController:
    def __init__(self):
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.history = list(self.settings.recent_history)
        self.cache = SubtitleCache(max_items=self.settings.cache_max_items)
        self.fetcher = SubtitleFetcher()
        self.fetcher.set_options(self.processing_options)
        self.notifier = Notifier()
        self.monitor = ClipboardMonitor(
            self.fetcher,
            on_status_change=self._handle_status_change,
            on_processed=self._handle_processed,
            notifier=self.notifier,
            subtitle_cache=self.cache,
            options_provider=lambda: self.processing_options,
        )
        self.watcher: ClipboardWatcher = create_watcher(self.handle_clipboard_change)
        self.is_running = False
        self._closing = False
        self._on_status: StatusHandler = lambda status, is_error: None
        self._on_history: HistoryHandler = lambda items: None
        self._on_cache: CacheHandler = lambda stats: None
        self._on_running: RunningHandler = lambda running: None

    @property
    def processing_options(self) -> ProcessingOptions:
        return ProcessingOptions(
            lang_code=self.settings.lang_code,
            include_timestamp=self.settings.include_timestamp,
        )

    def bind(
        self,
        *,
        on_status: StatusHandler,
        on_history: HistoryHandler,
        on_cache: CacheHandler,
        on_running: RunningHandler,
    ) -> None:
        self._on_status = on_status
        self._on_history = on_history
        self._on_cache = on_cache
        self._on_running = on_running

    def publish_initial_state(self) -> None:
        self._on_history(list(self.history))
        self._on_cache(self.cache.stats())
        self._on_running(self.is_running)

    def set_window_geometry(self, geometry: str) -> None:
        self.settings.window_geometry = geometry
        self._save_settings()

    def handle_clipboard_change(self) -> None:
        if not self.is_running or self._closing:
            return
        self.monitor.check_and_process()

    def start_monitoring(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.monitor.reset()
        self._on_running(True)
        self._handle_status_change("모니터링 중: YouTube URL을 복사하세요", False)
        self.watcher.start()

    def stop_monitoring(self) -> None:
        if not self.is_running:
            return
        self.is_running = False
        self.watcher.stop()
        self._on_running(False)
        self._handle_status_change("모니터링 정지", False)

    def toggle_monitoring(self) -> None:
        if self.is_running:
            self.stop_monitoring()
            return
        self.start_monitoring()

    def update_language(self, code: str) -> None:
        self.settings.lang_code = code
        self._apply_processing_settings_change(
            f"언어 변경: {code}{' (다음 URL부터 적용)' if self.is_running else ''} / 캐시 초기화"
        )

    def update_timestamp(self, include: bool) -> None:
        self.settings.include_timestamp = include
        state = "타임스탬프 포함" if include else "타임스탬프 제외"
        if self.is_running:
            state = f"{state} (다음 URL부터 적용)"
        self._apply_processing_settings_change(f"{state} / 캐시 초기화")

    def update_auto_start(self, enabled: bool) -> None:
        self.settings.auto_start = enabled
        self._save_settings()
        self._handle_status_change("자동 시작: 켜짐" if enabled else "자동 시작: 꺼짐", False)

    def update_cache_size(self, value: int) -> None:
        self.settings.cache_max_items = max(1, int(value))
        self.cache.set_max_items(self.settings.cache_max_items)
        self._save_settings()
        self._on_cache(self.cache.stats())
        self._handle_status_change(f"캐시 길이 변경: {self.settings.cache_max_items}", False)

    def clear_history(self) -> None:
        self.history.clear()
        self.settings.recent_history = []
        self._save_settings()
        self._on_history([])
        self._handle_status_change("최근 처리 내역을 비웠습니다", False)

    def shutdown(self, window_geometry: str) -> None:
        if self._closing:
            return
        self._closing = True
        self.settings.window_geometry = window_geometry
        self._save_settings()
        self.stop_monitoring()

    def _apply_processing_settings_change(self, status: str) -> None:
        self.fetcher.set_options(self.processing_options)
        self.monitor.reset_processed()
        self.cache.clear_all()
        self._save_settings()
        self._on_cache(self.cache.stats())
        self._handle_status_change(status, False)

    def _handle_status_change(self, status: str, is_error: bool) -> None:
        self._on_status(status, is_error)

    def _handle_processed(self, video_id: str, success: bool, detail: str) -> None:
        entry = HistoryEntry(
            time=datetime.now().strftime("%H:%M:%S"),
            status="성공" if success else "실패",
            video_id=video_id,
            detail=detail,
        )
        self.history.insert(0, entry)
        self.history = self.history[:20]
        self.settings.recent_history = list(self.history)
        self._save_settings()
        self._on_history(list(self.history))
        self._on_cache(self.cache.stats())

    def _save_settings(self) -> None:
        self.settings_store.save(self.settings)
