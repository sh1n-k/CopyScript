"""YouTube 자막 클립보드 복사 앱 - 메인 GUI"""

from __future__ import annotations

import json
from datetime import datetime
import tkinter as tk
from tkinter import ttk

from app_paths import get_settings_path
from clipboard_monitor import ClipboardMonitor
from clipboard_watchers import create_watcher
from notifier import Notifier
from subtitle_fetcher import SubtitleFetcher, SUPPORTED_LANGUAGES


DEFAULT_GEOMETRY = "460x430"
MAX_HISTORY_ITEMS = 20


class App:
    """메인 애플리케이션 클래스"""

    def __init__(self):
        self.settings_path = get_settings_path()
        self.settings = self._load_settings()
        self.recent_history: list[dict[str, str]] = list(self.settings.get("recent_history", []))

        self.root = tk.Tk()
        self.root.title("YouTube 자막 복사")
        self.root.geometry(DEFAULT_GEOMETRY)
        self.root.resizable(False, False)

        saved_geometry = self.settings.get("window_geometry")
        if isinstance(saved_geometry, str) and saved_geometry:
            self.root.geometry(saved_geometry)

        self.is_running = False
        self._closing = False

        # 자막 추출기, 알림, 모니터 초기화
        preferred_lang = self.settings.get("lang_code", "ko")
        include_timestamp = bool(self.settings.get("include_timestamp", False))

        self.fetcher = SubtitleFetcher(preferred_lang, include_timestamp)
        self.notifier = Notifier()
        self.monitor = ClipboardMonitor(
            self.fetcher,
            self._on_status_change,
            self._on_processed,
            self.notifier,
        )

        # 플랫폼별 감지기 (Windows=이벤트, macOS=changeCount)
        self.watcher = create_watcher(self._on_clipboard_change)

        self._build_language_maps()
        self._setup_ui()
        self._refresh_history_ui()
        if not saved_geometry:
            self._center_window()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if self.auto_start_var.get():
            self.root.after(120, self._start_monitor)

    def _default_settings(self) -> dict:
        return {
            "lang_code": "ko",
            "include_timestamp": False,
            "auto_start": True,
            "window_geometry": "",
            "recent_history": [],
        }

    def _load_settings(self) -> dict:
        """저장된 사용자 설정 로드"""
        defaults = self._default_settings()
        try:
            if self.settings_path.exists():
                loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    defaults.update(loaded)
        except Exception:
            pass

        recent_history = defaults.get("recent_history")
        if not isinstance(recent_history, list):
            defaults["recent_history"] = []
        else:
            sanitized = []
            for item in recent_history[:MAX_HISTORY_ITEMS]:
                if not isinstance(item, dict):
                    continue
                sanitized.append(
                    {
                        "time": str(item.get("time", "")),
                        "status": str(item.get("status", "")),
                        "video_id": str(item.get("video_id", "")),
                        "detail": str(item.get("detail", "")),
                    }
                )
            defaults["recent_history"] = sanitized
        return defaults

    def _save_settings(self) -> None:
        """현재 상태를 설정 파일에 저장"""
        try:
            self.settings["lang_code"] = self._current_language_code()
            self.settings["include_timestamp"] = bool(self.timestamp_var.get())
            self.settings["auto_start"] = bool(self.auto_start_var.get())
            self.settings["window_geometry"] = self.root.geometry()
            self.settings["recent_history"] = self.recent_history[:MAX_HISTORY_ITEMS]

            self.settings_path.write_text(
                json.dumps(self.settings, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _build_language_maps(self) -> None:
        self.lang_options = [f"{name} ({code})" for name, code in SUPPORTED_LANGUAGES]
        self.label_to_code = {label: code for label, (_, code) in zip(self.lang_options, SUPPORTED_LANGUAGES)}
        self.code_to_label = {code: label for label, (_, code) in zip(self.lang_options, SUPPORTED_LANGUAGES)}

    def _current_language_code(self) -> str:
        selected = self.lang_combo.get()
        code = self.label_to_code.get(selected)
        if code:
            return code
        if "(" in selected and selected.endswith(")"):
            return selected.split("(")[-1].rstrip(")")
        return "ko"

    def _setup_ui(self):
        """UI 구성"""
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 언어 선택
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(lang_frame, text="언어:").pack(side=tk.LEFT)

        initial_lang = self.code_to_label.get(self.settings.get("lang_code", "ko"), self.lang_options[0])
        self.lang_var = tk.StringVar(value=initial_lang)
        self.lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.lang_var,
            values=self.lang_options,
            state="readonly",
            width=24,
        )
        self.lang_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)

        # 옵션
        option_frame = ttk.Frame(main_frame)
        option_frame.pack(fill=tk.X, pady=(0, 6))

        self.timestamp_var = tk.BooleanVar(value=bool(self.settings.get("include_timestamp", False)))
        self.timestamp_check = ttk.Checkbutton(
            option_frame,
            text="타임스탬프 포함 [00:00]",
            variable=self.timestamp_var,
            command=self._on_timestamp_change,
        )
        self.timestamp_check.pack(anchor=tk.W)

        self.auto_start_var = tk.BooleanVar(value=bool(self.settings.get("auto_start", False)))
        self.auto_start_check = ttk.Checkbutton(
            option_frame,
            text="앱 실행 시 모니터링 자동 시작",
            variable=self.auto_start_var,
            command=self._on_auto_start_change,
        )
        self.auto_start_check.pack(anchor=tk.W)

        self.hint_label = ttk.Label(
            main_frame,
            text="옵션 변경은 즉시 저장되며, 모니터링 중에는 다음 URL부터 적용됩니다.",
            foreground="gray",
        )
        self.hint_label.pack(fill=tk.X, pady=(0, 8))

        # 버튼
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.toggle_btn = ttk.Button(btn_frame, text="▶ 시작", command=self._toggle_monitor, width=12)
        self.toggle_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_btn = ttk.Button(btn_frame, text="내역 지우기", command=self._clear_history, width=12)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.quit_btn = ttk.Button(btn_frame, text="종료", command=self._on_close, width=12)
        self.quit_btn.pack(side=tk.LEFT)

        # 상태 표시
        self.status_var = tk.StringVar(value="시작 버튼을 누른 뒤 YouTube URL을 복사하세요")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(main_frame, text="최근 처리 내역 (최신순)").pack(anchor=tk.W)

        history_frame = ttk.Frame(main_frame)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.history_list = tk.Listbox(history_frame, height=9, activestyle="none")
        self.history_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.history_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_list.yview)
        self.history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_list.config(yscrollcommand=self.history_scroll.set)

    def _center_window(self):
        """창을 화면 중앙에 배치"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _on_language_change(self, event=None):
        """언어 선택 변경 시"""
        code = self._current_language_code()
        self.fetcher.set_language(code)
        self._save_settings()
        suffix = " (다음 URL부터 적용)" if self.is_running else ""
        self._update_status(f"언어 변경: {code}{suffix}")

    def _on_timestamp_change(self):
        """타임스탬프 옵션 변경 시"""
        include = self.timestamp_var.get()
        self.fetcher.set_timestamp(include)
        self._save_settings()
        status = "타임스탬프 포함" if include else "타임스탬프 제외"
        if self.is_running:
            status = f"{status} (다음 URL부터 적용)"
        self._update_status(status)

    def _on_auto_start_change(self):
        """자동 시작 옵션 변경 시"""
        self._save_settings()
        enabled = self.auto_start_var.get()
        status = "자동 시작: 켜짐" if enabled else "자동 시작: 꺼짐"
        self._update_status(status)

    def _toggle_monitor(self):
        """모니터링 시작/정지 토글"""
        if self.is_running:
            self._stop_monitor()
        else:
            self._start_monitor()

    def _start_monitor(self):
        """모니터링 시작"""
        if self.is_running:
            return

        self.is_running = True
        self.monitor.reset()

        self.toggle_btn.config(text="⏹ 정지")
        self._update_status("모니터링 중: YouTube URL을 복사하세요")

        # 감지기 시작
        self.watcher.start()

    def _stop_monitor(self):
        """모니터링 정지"""
        if not self.is_running:
            return

        self.is_running = False

        # 감지기 정지(스레드 join 포함)
        self.watcher.stop()

        self.toggle_btn.config(text="▶ 시작")
        self._update_status("모니터링 정지")

    def _on_clipboard_change(self) -> None:
        """Watcher 스레드에서 호출됨. 실제 처리는 monitor에서."""
        if not self.is_running or self._closing:
            return
        self.monitor.check_and_process()

    def _on_status_change(self, status: str, is_error: bool = False):
        """상태 변경 콜백 (스레드 안전)"""
        # destroy 이후 after 호출 방지
        if self._closing or not self.root.winfo_exists():
            return
        self.root.after(0, lambda: self._update_status(status, is_error))

    def _on_processed(self, video_id: str, success: bool, detail: str):
        """처리 결과 콜백 (스레드 안전)"""
        if self._closing or not self.root.winfo_exists():
            return
        self.root.after(0, lambda: self._append_history(video_id, success, detail))

    def _update_status(self, status: str, is_error: bool = False):
        """상태 라벨 업데이트"""
        self.status_var.set(status)
        color = "red" if is_error else ("green" if "완료" in status else "gray")
        self.status_label.config(foreground=color)

    def _append_history(self, video_id: str, success: bool, detail: str):
        """최근 처리 내역 추가"""
        short_id = f"{video_id[:8]}..." if len(video_id) > 8 else video_id
        item = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "status": "성공" if success else "실패",
            "video_id": short_id,
            "detail": detail,
        }
        self.recent_history.insert(0, item)
        self.recent_history = self.recent_history[:MAX_HISTORY_ITEMS]
        self._refresh_history_ui()
        self._save_settings()

    def _refresh_history_ui(self):
        """최근 처리 내역 화면 갱신"""
        self.history_list.delete(0, tk.END)
        for item in self.recent_history:
            detail = item.get("detail", "")
            if len(detail) > 40:
                detail = f"{detail[:37]}..."
            line = (
                f"{item.get('time', '--:--:--')} | "
                f"{item.get('status', '-')} | "
                f"{item.get('video_id', '-')} | "
                f"{detail}"
            )
            self.history_list.insert(tk.END, line)

    def _clear_history(self):
        """최근 처리 내역 초기화"""
        self.recent_history.clear()
        self._refresh_history_ui()
        self._save_settings()
        self._update_status("최근 처리 내역을 비웠습니다")

    def _on_close(self):
        """앱 종료"""
        if self._closing:
            return
        self._closing = True

        try:
            self._save_settings()
            self._stop_monitor()
        finally:
            # after 큐에 남은 콜백이 있어도 _closing 가드가 막아줌
            self.root.destroy()

    def run(self):
        """앱 실행"""
        self.root.mainloop()


def main():
    App().run()


if __name__ == "__main__":
    main()
