from __future__ import annotations

from collections.abc import Callable
from collections import OrderedDict
import logging
import platform
import threading
import time
from typing import Literal, Protocol

import pyperclip

from copyscript.config.models import ProcessingOptions
from copyscript.core.url_parser import extract_video_id

logger = logging.getLogger(__name__)
StatusCallback = Callable[[str, bool], None]
ProcessedCallback = Callable[[str, bool, str], None]
OptionsProvider = Callable[[], ProcessingOptions]
RecheckCallback = Callable[[], None]

ClipboardWriteStatus = Literal["ok", "mismatch", "read_error", "copy_error"]

_WRITE_MAX_ATTEMPTS = 3
_WRITE_RETRY_DELAYS_SEC = (0.05, 0.1)
_POST_COPY_SETTLE_SEC = 0.03
_PASTE_VERIFY_TIMEOUT_SEC = 0.75


class FetcherLike(Protocol):
    def fetch(
        self, video_id: str, options: ProcessingOptions | None = None
    ) -> tuple[str, str | None]: ...

    def get_options(self) -> ProcessingOptions: ...


class CacheLike(Protocol):
    def get(
        self, video_id: str, lang_code: str, include_timestamp: bool
    ) -> str | None: ...

    def put(
        self, video_id: str, lang_code: str, include_timestamp: bool, text: str
    ) -> None: ...


class NotifierLike(Protocol):
    def notify(self, title: str, message: str) -> None: ...


def _normalize_clipboard_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


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
        on_need_recheck: RecheckCallback | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.on_status_change = on_status_change
        self.on_processed = on_processed
        self.notifier = notifier
        self.subtitle_cache = subtitle_cache
        self.options_provider = options_provider
        self.on_need_recheck = on_need_recheck
        self._last_clipboard = ""
        self._max_processed = max(10, int(max_processed))
        self._processed_ids: OrderedDict[str, None] = OrderedDict()
        self._busy = False
        # One automatic recheck per video after a clipboard write failure.
        self._auto_recheck_video_id: str | None = None

    def _current_options(self) -> ProcessingOptions:
        if self.options_provider:
            return self.options_provider()
        return self.fetcher.get_options()

    def _update_status(self, status: str, is_error: bool = False) -> None:
        if self.on_status_change:
            try:
                self.on_status_change(status, is_error)
            except Exception:
                logger.exception("Unhandled error in status callback")

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
                logger.exception("Unhandled error in processed callback")

    def _request_recheck(self) -> None:
        if not self.on_need_recheck:
            return
        try:
            self.on_need_recheck()
        except Exception:
            logger.exception("Unhandled error in recheck callback")

    def _clipboard_access_error(self) -> str:
        system = platform.system()
        if system == "Darwin":
            return (
                "클립보드 접근 실패 (macOS: 시스템 설정 > 개인정보 보호 및 보안 확인)"
            )
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

    def _clipboard_verify_mismatch_error(self) -> str:
        return "클립보드 복사 실패 (내용이 반영되지 않음)"

    def _clipboard_verify_read_error(self) -> str:
        system = platform.system()
        if system == "Darwin":
            return "클립보드 확인 실패 (macOS: 클립보드 접근 권한 확인)"
        if system == "Windows":
            return "클립보드 확인 실패 (다른 앱의 클립보드 점유 여부 확인)"
        return "클립보드 확인 실패"

    def _friendly_error(self, error: str) -> str:
        if "자막이 비활성화된 영상입니다" in error:
            return f"{error} (다른 영상 또는 자동 생성 자막 영상으로 시도)"
        if "영상을 찾을 수 없습니다" in error:
            return f"{error} (삭제/비공개 여부 확인)"
        if "사용 가능한 자막이 없습니다" in error:
            return f"{error} (언어를 '영상 기본 언어' 또는 'Auto (any)'로 시도)"
        return error

    def _message_for_write_status(self, status: ClipboardWriteStatus) -> str:
        if status == "mismatch":
            return self._clipboard_verify_mismatch_error()
        if status == "read_error":
            return self._clipboard_verify_read_error()
        return self._clipboard_copy_error()

    def _paste_with_timeout(
        self, timeout_sec: float = _PASTE_VERIFY_TIMEOUT_SEC
    ) -> tuple[str | None, bool]:
        box: list[object] = []
        error: list[Exception] = []

        def worker() -> None:
            try:
                box.append(pyperclip.paste())
            except Exception as exc:
                error.append(exc)

        thread = threading.Thread(
            target=worker, name="clipboard-paste-verify", daemon=True
        )
        thread.start()
        thread.join(timeout=timeout_sec)
        if thread.is_alive():
            logger.warning(
                "Clipboard paste verification timed out after %ss", timeout_sec
            )
            return None, False
        if error:
            logger.debug(
                "Clipboard paste verification failed: %s",
                error[0],
                exc_info=error[0],
            )
            return None, False
        if not box:
            return None, False
        value = box[0]
        if not isinstance(value, str):
            return None, False
        return value, True

    def _copy_and_verify(self, text: str) -> ClipboardWriteStatus:
        last_status: ClipboardWriteStatus = "copy_error"
        for attempt in range(_WRITE_MAX_ATTEMPTS):
            try:
                pyperclip.copy(text)
            except Exception:
                last_status = "copy_error"
                logger.debug(
                    "Clipboard copy failed on attempt %s/%s",
                    attempt + 1,
                    _WRITE_MAX_ATTEMPTS,
                    exc_info=True,
                )
            else:
                if _POST_COPY_SETTLE_SEC > 0:
                    time.sleep(_POST_COPY_SETTLE_SEC)
                actual, read_ok = self._paste_with_timeout()
                if not read_ok:
                    last_status = "read_error"
                elif _normalize_clipboard_text(
                    actual or ""
                ) == _normalize_clipboard_text(text):
                    return "ok"
                else:
                    last_status = "mismatch"
                    logger.debug(
                        "Clipboard verify mismatch on attempt %s/%s "
                        "(expected_len=%s actual_len=%s)",
                        attempt + 1,
                        _WRITE_MAX_ATTEMPTS,
                        len(text),
                        len(actual or ""),
                    )
            if attempt < _WRITE_MAX_ATTEMPTS - 1:
                delay = _WRITE_RETRY_DELAYS_SEC[
                    min(attempt, len(_WRITE_RETRY_DELAYS_SEC) - 1)
                ]
                time.sleep(delay)
        return last_status

    def _fail_clipboard_write(
        self, video_id: str, status: ClipboardWriteStatus
    ) -> None:
        message = self._message_for_write_status(status)
        self._last_clipboard = ""
        self._update_status(message, is_error=True)
        self._notify("자막 복사 실패", f"{video_id} - {message}")
        self._emit_processed(video_id, False, message)
        # Allow one automatic same-URL retry via watcher baseline invalidation.
        if self._auto_recheck_video_id != video_id:
            self._auto_recheck_video_id = video_id
            self._request_recheck()
        else:
            self._auto_recheck_video_id = None

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
            if (
                not isinstance(current, str)
                or not current
                or current == self._last_clipboard
            ):
                return False
            self._last_clipboard = current
            current_video_id = extract_video_id(current)
            if not current_video_id:
                return False
            options = self._current_options()
            prefer_cache = (
                current_video_id in self._processed_ids
                or self._auto_recheck_video_id == current_video_id
            )
            if prefer_cache:
                if current_video_id in self._processed_ids:
                    self._processed_ids.move_to_end(current_video_id)
                cache_result = self._try_copy_from_cache(current_video_id, options)
                if cache_result is True:
                    return True
                if cache_result is False:
                    # Write attempted and failed; do not fall through to fetch.
                    return False
                if current_video_id in self._processed_ids:
                    self._update_status(
                        f"이미 처리됨(캐시 없음): {current_video_id[:8]}... 재시도"
                    )
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
            # Preserve extract result even if clipboard write later fails.
            self._put_cache(current_video_id, text, options)
            self._update_status("클립보드 복사 중...")
            write_status = self._copy_and_verify(text)
            if write_status != "ok":
                self._fail_clipboard_write(current_video_id, write_status)
                return False
            self._last_clipboard = text
            self._mark_processed(current_video_id)
            self._auto_recheck_video_id = None
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
        self._auto_recheck_video_id = None

    def reset_processed(self) -> None:
        self._processed_ids.clear()
        self._auto_recheck_video_id = None

    def _try_copy_from_cache(
        self, video_id: str, options: ProcessingOptions
    ) -> bool | None:
        """Return True on success, False on write failure, None on cache miss."""
        if not self.subtitle_cache:
            return None
        cached_text = self.subtitle_cache.get(
            video_id, options.lang_code, options.include_timestamp
        )
        if not cached_text:
            return None
        self._update_status("캐시 자막 복사 중...")
        write_status = self._copy_and_verify(cached_text)
        if write_status != "ok":
            self._fail_clipboard_write(video_id, write_status)
            return False
        self._last_clipboard = cached_text
        self._mark_processed(video_id)
        self._auto_recheck_video_id = None
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
            self.subtitle_cache.put(
                video_id, options.lang_code, options.include_timestamp, text
            )
        except Exception:
            logger.exception("Failed to store subtitle cache entry for %s", video_id)
