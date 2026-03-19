from __future__ import annotations

from collections import OrderedDict
import platform
from typing import Callable, Protocol

import pyperclip

from copyscript.config.models import ProcessingOptions
from copyscript.core.url_parser import extract_video_id

StatusCallback = Callable[[str, bool], None]
ProcessedCallback = Callable[[str, bool, str], None]
OptionsProvider = Callable[[], ProcessingOptions]


class FetcherLike(Protocol):
    def fetch(self, video_id: str, options: ProcessingOptions | None = None) -> tuple[str, str | None]:
        ...

    def get_options(self) -> ProcessingOptions:
        ...


class CacheLike(Protocol):
    def get(self, video_id: str, lang_code: str, include_timestamp: bool) -> str | None:
        ...

    def put(self, video_id: str, lang_code: str, include_timestamp: bool, text: str) -> None:
        ...


class NotifierLike(Protocol):
    def notify(self, title: str, message: str) -> None:
        ...


class ClipboardMonitor:
    def __init__(
        self,
        fetcher: FetcherLike,
        on_status_change: StatusCallback | None = None,
        on_processed: ProcessedCallback | None = None,
        notifier: NotifierLike | None = None,
        subtitle_cache: CacheLike | None = None,
        max_processed: int = 100,
        options_provider: OptionsProvider | None = None,
    ):
        self.fetcher = fetcher
        self.on_status_change = on_status_change
        self.on_processed = on_processed
        self.notifier = notifier
        self.subtitle_cache = subtitle_cache
        self.options_provider = options_provider
        self._last_clipboard = ""
        self._max_processed = max(10, int(max_processed))
        self._processed_ids: OrderedDict[str, None] = OrderedDict()
        self._busy = False

    def _current_options(self) -> ProcessingOptions:
        if self.options_provider:
            return self.options_provider()
        return self.fetcher.get_options()

    def _update_status(self, status: str, is_error: bool = False) -> None:
        if self.on_status_change:
            try:
                self.on_status_change(status, is_error)
            except Exception:
                pass

    def _mark_processed(self, video_id: str) -> None:
        if video_id in self._processed_ids:
            self._processed_ids.move_to_end(video_id)
            return
        self._processed_ids[video_id] = None
        if len(self._processed_ids) > self._max_processed:
            self._processed_ids.popitem(last=False)

    def _notify(self, title: str, message: str) -> None:
        if self.notifier:
            self.notifier.notify(title, message)

    def _emit_processed(self, video_id: str, success: bool, detail: str) -> None:
        if self.on_processed:
            try:
                self.on_processed(video_id, success, detail)
            except Exception:
                pass

    def _clipboard_access_error(self) -> str:
        system = platform.system()
        if system == "Darwin":
            return "클립보드 접근 실패 (macOS: 시스템 설정 > 개인정보 보호 및 보안 확인)"
        if system == "Windows":
            return "클립보드 접근 실패 (다른 앱의 클립보드 점유 여부 확인)"
        return "클립보드 접근 실패"

    def _clipboard_copy_error(self) -> str:
        system = platform.system()
        if system == "Darwin":
            return "클립보드 복사 실패 (macOS: 클립보드 접근 권한 확인)"
        if system == "Windows":
            return "클립보드 복사 실패 (보안 앱/원격 앱 간섭 여부 확인)"
        return "클립보드 복사 실패"

    def _friendly_error(self, error: str) -> str:
        if "자막이 비활성화된 영상입니다" in error:
            return f"{error} (다른 영상 또는 자동 생성 자막 영상으로 시도)"
        if "영상을 찾을 수 없습니다" in error:
            return f"{error} (삭제/비공개 여부 확인)"
        if "사용 가능한 자막이 없습니다" in error:
            return f"{error} (언어를 '영상 기본 언어' 또는 'Auto (any)'로 시도)"
        return error

    def check_and_process(self) -> bool:
        current_video_id: str | None = None
        if self._busy:
            return False
        self._busy = True
        try:
            try:
                current = pyperclip.paste()
            except Exception:
                self._update_status(self._clipboard_access_error(), is_error=True)
                return False
            if not isinstance(current, str) or not current or current == self._last_clipboard:
                return False
            self._last_clipboard = current
            current_video_id = extract_video_id(current)
            if not current_video_id:
                return False
            options = self._current_options()
            if current_video_id in self._processed_ids:
                self._processed_ids.move_to_end(current_video_id)
                if self._try_copy_from_cache(current_video_id, options):
                    return True
                self._update_status(f"이미 처리됨(캐시 없음): {current_video_id[:8]}... 재시도")
            self._update_status(f"URL 감지됨: {current_video_id[:8]}...")
            self._update_status(f"자막 추출 중: {current_video_id}...")
            text, error = self.fetcher.fetch(current_video_id, options=options)
            if error:
                error_message = self._friendly_error(error)
                self._update_status(error_message, is_error=True)
                self._notify("자막 복사 실패", f"{current_video_id} - {error_message}")
                self._emit_processed(current_video_id, False, error_message)
                return False
            if not text:
                status_message = "자막이 비어있습니다"
                self._update_status(status_message, is_error=True)
                self._notify("자막 복사 실패", f"{current_video_id} - {status_message}")
                self._emit_processed(current_video_id, False, status_message)
                return False
            self._update_status("클립보드 복사 중...")
            try:
                pyperclip.copy(text)
            except Exception:
                status_message = self._clipboard_copy_error()
                self._update_status(status_message, is_error=True)
                self._notify("자막 복사 실패", f"{current_video_id} - {status_message}")
                self._emit_processed(current_video_id, False, status_message)
                return False
            self._last_clipboard = text
            self._mark_processed(current_video_id)
            self._put_cache(current_video_id, text, options)
            line_count = text.count("\n") + 1
            status_message = f"완료! {line_count}줄 복사됨"
            self._update_status(status_message)
            self._notify("자막 복사 완료", f"{current_video_id} - {line_count}줄")
            self._emit_processed(current_video_id, True, f"{line_count}줄 복사")
            return True
        except Exception as error:
            status_message = f"오류: {str(error)}"
            self._update_status(status_message, is_error=True)
            if current_video_id:
                self._notify("자막 복사 실패", f"{current_video_id} - {status_message}")
                self._emit_processed(current_video_id, False, status_message)
            return False
        finally:
            self._busy = False

    def reset(self) -> None:
        self._last_clipboard = ""
        self._busy = False

    def reset_processed(self) -> None:
        self._processed_ids.clear()

    def _try_copy_from_cache(self, video_id: str, options: ProcessingOptions) -> bool:
        if not self.subtitle_cache:
            return False
        cached_text = self.subtitle_cache.get(video_id, options.lang_code, options.include_timestamp)
        if not cached_text:
            return False
        self._update_status("캐시 자막 복사 중...")
        try:
            pyperclip.copy(cached_text)
        except Exception:
            status_message = self._clipboard_copy_error()
            self._update_status(status_message, is_error=True)
            self._notify("자막 복사 실패", f"{video_id} - {status_message}")
            self._emit_processed(video_id, False, status_message)
            return False
        self._last_clipboard = cached_text
        line_count = cached_text.count("\n") + 1
        status_message = f"이미 처리됨: 캐시 재복사 완료 ({line_count}줄)"
        self._update_status(status_message)
        self._notify("자막 재복사 완료", f"{video_id} - {line_count}줄")
        self._emit_processed(video_id, True, f"캐시 재복사 {line_count}줄")
        return True

    def _put_cache(self, video_id: str, text: str, options: ProcessingOptions) -> None:
        if not self.subtitle_cache:
            return
        try:
            self.subtitle_cache.put(video_id, options.lang_code, options.include_timestamp, text)
        except Exception:
            pass
