"""클립보드 모니터링 모듈 (YouTube URL 감지 → 자막을 클립보드로 복사)"""

from __future__ import annotations

from collections import OrderedDict
import platform
from typing import Callable, Optional

import pyperclip

from subtitle_fetcher import SubtitleFetcher
from subtitle_cache import SubtitleCache
from notifier import Notifier
from url_parser import extract_video_id


StatusCallback = Callable[[str, bool], None]
ProcessedCallback = Callable[[str, bool, str], None]


class ClipboardMonitor:
    """클립보드를 확인하고 YouTube URL이면 자막을 복사합니다.

    - 동시 실행 방지(락)
    - 동일 video_id 중복 처리 방지(LRU 캐시)
    """

    def __init__(
        self,
        fetcher: SubtitleFetcher,
        on_status_change: Optional[StatusCallback] = None,
        on_processed: Optional[ProcessedCallback] = None,
        notifier: Optional[Notifier] = None,
        subtitle_cache: Optional[SubtitleCache] = None,
        max_processed: int = 100,
    ):
        """
        Args:
            fetcher: SubtitleFetcher 인스턴스
            on_status_change: 상태 변경 콜백 (status: str, is_error: bool)
            on_processed: 처리 결과 콜백 (video_id, success, detail)
            notifier: Notifier 인스턴스 (선택)
            subtitle_cache: 자막 텍스트 캐시 (선택)
            max_processed: 처리한 video_id LRU 캐시 최대 크기
        """
        self.fetcher = fetcher
        self.on_status_change = on_status_change
        self.on_processed = on_processed
        self.notifier = notifier
        self.subtitle_cache = subtitle_cache

        self._last_clipboard: str = ""
        self._max_processed = max(10, int(max_processed))

        # OrderedDict: insertion-ordered → LRU 흉내
        self._processed_ids: OrderedDict[str, None] = OrderedDict()

        # 재진입/동시 실행 방지용 플래그(락보다 가벼움)
        self._busy = False

    def _update_status(self, status: str, is_error: bool = False) -> None:
        """상태 업데이트 콜백 호출"""
        if self.on_status_change:
            try:
                self.on_status_change(status, is_error)
            except Exception:
                # GUI 종료 중 등 콜백 실패는 조용히 무시
                pass

    def _mark_processed(self, video_id: str) -> None:
        """LRU 캐시 갱신"""
        if video_id in self._processed_ids:
            self._processed_ids.move_to_end(video_id)
            return
        self._processed_ids[video_id] = None
        if len(self._processed_ids) > self._max_processed:
            # 가장 오래된 항목 제거
            self._processed_ids.popitem(last=False)

    def _notify(self, title: str, message: str) -> None:
        """알림 표시 (옵션)"""
        if self.notifier:
            self.notifier.notify(title, message)

    def _emit_processed(self, video_id: str, success: bool, detail: str) -> None:
        """처리 결과 콜백 호출"""
        if self.on_processed:
            try:
                self.on_processed(video_id, success, detail)
            except Exception:
                pass

    def _clipboard_access_error(self) -> str:
        """OS별 클립보드 접근 실패 안내 문구"""
        system = platform.system()
        if system == "Darwin":
            return "클립보드 접근 실패 (macOS: 시스템 설정 > 개인정보 보호 및 보안 확인)"
        if system == "Windows":
            return "클립보드 접근 실패 (다른 앱의 클립보드 점유 여부 확인)"
        return "클립보드 접근 실패"

    def _clipboard_copy_error(self) -> str:
        """OS별 클립보드 복사 실패 안내 문구"""
        system = platform.system()
        if system == "Darwin":
            return "클립보드 복사 실패 (macOS: 클립보드 접근 권한 확인)"
        if system == "Windows":
            return "클립보드 복사 실패 (보안 앱/원격 앱 간섭 여부 확인)"
        return "클립보드 복사 실패"

    def _friendly_error(self, error: str) -> str:
        """자주 발생하는 오류에 해결 힌트 추가"""
        if "자막이 비활성화된 영상입니다" in error:
            return f"{error} (다른 영상 또는 자동 생성 자막 영상으로 시도)"
        if "영상을 찾을 수 없습니다" in error:
            return f"{error} (삭제/비공개 여부 확인)"
        if "사용 가능한 자막이 없습니다" in error:
            return f"{error} (언어를 '영상 기본 언어' 또는 'Auto (any)'로 시도)"
        return error

    def check_and_process(self) -> bool:
        """
        클립보드를 확인하고 YouTube URL이면 자막을 복사합니다.

        Returns:
            처리 여부 (True: 자막 복사됨, False: 처리 안함)
        """
        current_video_id: Optional[str] = None
        if self._busy:
            return False

        self._busy = True
        try:
            try:
                current = pyperclip.paste()
            except Exception:
                # 클립보드 접근 실패 (환경/권한/툴 부재 등)
                self._update_status(self._clipboard_access_error(), is_error=True)
                return False

            if not isinstance(current, str) or not current:
                return False

            if current == self._last_clipboard:
                return False

            self._last_clipboard = current

            current_video_id = extract_video_id(current)
            if not current_video_id:
                return False

            if current_video_id in self._processed_ids:
                self._processed_ids.move_to_end(current_video_id)
                if self._try_copy_from_cache(current_video_id):
                    return True
                self._update_status(
                    f"이미 처리됨(캐시 없음): {current_video_id[:8]}... 재시도",
                )

            self._update_status(f"URL 감지됨: {current_video_id[:8]}...")
            self._update_status(f"자막 추출 중: {current_video_id}...")

            text, error = self.fetcher.fetch(current_video_id)

            if error:
                error_msg = self._friendly_error(error)
                self._update_status(error_msg, is_error=True)
                self._notify("자막 복사 실패", f"{current_video_id} - {error_msg}")
                self._emit_processed(current_video_id, False, error_msg)
                return False

            if not text:
                status_msg = "자막이 비어있습니다"
                self._update_status(status_msg, is_error=True)
                self._notify("자막 복사 실패", f"{current_video_id} - {status_msg}")
                self._emit_processed(current_video_id, False, status_msg)
                return False

            self._update_status("클립보드 복사 중...")
            # 클립보드에 자막 복사
            try:
                pyperclip.copy(text)
            except Exception:
                status_msg = self._clipboard_copy_error()
                self._update_status(status_msg, is_error=True)
                self._notify("자막 복사 실패", f"{current_video_id} - {status_msg}")
                self._emit_processed(current_video_id, False, status_msg)
                return False

            # 방금 복사한 자막이 다시 감지되지 않도록
            self._last_clipboard = text

            self._mark_processed(current_video_id)
            self._put_cache(current_video_id, text)

            line_count = text.count("\n") + 1
            status_msg = f"완료! {line_count}줄 복사됨"
            self._update_status(status_msg)

            self._notify("자막 복사 완료", f"{current_video_id} - {line_count}줄")
            self._emit_processed(current_video_id, True, f"{line_count}줄 복사")

            return True

        except Exception as e:
            status_msg = f"오류: {str(e)}"
            self._update_status(status_msg, is_error=True)
            if current_video_id:
                self._notify("자막 복사 실패", f"{current_video_id} - {status_msg}")
                self._emit_processed(current_video_id, False, status_msg)
            return False
        finally:
            self._busy = False

    def reset(self) -> None:
        """상태 초기화"""
        self._last_clipboard = ""
        self._busy = False

    def reset_processed(self) -> None:
        """이미 처리한 video_id 캐시 초기화"""
        self._processed_ids.clear()

    def _try_copy_from_cache(self, video_id: str) -> bool:
        if not self.subtitle_cache:
            return False
        cached_text = self.subtitle_cache.get(
            video_id,
            self.fetcher.preferred_lang,
            self.fetcher.include_timestamp,
        )
        if not cached_text:
            return False

        self._update_status("캐시 자막 복사 중...")
        try:
            pyperclip.copy(cached_text)
        except Exception:
            status_msg = self._clipboard_copy_error()
            self._update_status(status_msg, is_error=True)
            self._notify("자막 복사 실패", f"{video_id} - {status_msg}")
            self._emit_processed(video_id, False, status_msg)
            return False

        self._last_clipboard = cached_text
        line_count = cached_text.count("\n") + 1
        status_msg = f"이미 처리됨: 캐시 재복사 완료 ({line_count}줄)"
        self._update_status(status_msg)
        self._notify("자막 재복사 완료", f"{video_id} - {line_count}줄")
        self._emit_processed(video_id, True, f"캐시 재복사 {line_count}줄")
        return True

    def _put_cache(self, video_id: str, text: str) -> None:
        if not self.subtitle_cache:
            return
        try:
            self.subtitle_cache.put(
                video_id,
                self.fetcher.preferred_lang,
                self.fetcher.include_timestamp,
                text,
            )
        except Exception:
            pass
