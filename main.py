"""CopyScript - 메인 GUI"""

from __future__ import annotations

import json
import platform
from datetime import datetime
import tkinter as tk
from tkinter import ttk

from app_paths import get_settings_path
from clipboard_monitor import ClipboardMonitor
from clipboard_watchers import create_watcher
from notifier import Notifier
from subtitle_cache import SubtitleCache
from subtitle_fetcher import SubtitleFetcher, SUPPORTED_LANGUAGES

IS_MACOS = platform.system() == "Darwin"


DEFAULT_GEOMETRY = "460x620"
MAX_HISTORY_ITEMS = 20
CACHE_GRAPH_WIDTH = 420
CACHE_GRAPH_HEIGHT = 60
MIN_WINDOW_WIDTH = 460
MIN_WINDOW_HEIGHT = 620


class App:
    """메인 애플리케이션 클래스"""

    def __init__(self):
        self.settings_path = get_settings_path()
        self.settings = self._load_settings()
        self.recent_history: list[dict[str, str]] = list(self.settings.get("recent_history", []))
        self.cache = SubtitleCache(max_items=int(self.settings.get("cache_max_items", 100)))

        self.root = tk.Tk()
        self.root.title("CopyScript")
        self.root.geometry(DEFAULT_GEOMETRY)
        self.root.resizable(False, False)
        if IS_MACOS:
            # macOS에서는 시작 시 설정 창을 숨기고 메뉴바에서만 접근
            self.root.withdraw()

        saved_geometry = self.settings.get("window_geometry")
        if isinstance(saved_geometry, str) and saved_geometry:
            self.root.geometry(self._normalize_geometry(saved_geometry))

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
            subtitle_cache=self.cache,
        )

        # 플랫폼별 감지기 (Windows=이벤트, macOS=changeCount)
        self.watcher = create_watcher(self._on_clipboard_change)

        self._build_language_maps()
        self._setup_ui()
        self._refresh_history_ui()
        self._refresh_cache_status()
        self._history_tooltip: tk.Toplevel | None = None
        self._history_tooltip_row: int | None = None
        if not saved_geometry:
            self._center_window()

        self.menubar = None
        if IS_MACOS:
            self._setup_menubar()
            self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        else:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if self.auto_start_var.get():
            self.root.after(120, self._start_monitor)

    def _default_settings(self) -> dict:
        return {
            "lang_code": "ko",
            "include_timestamp": False,
            "auto_start": True,
            "cache_max_items": 100,
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

        try:
            defaults["cache_max_items"] = max(1, int(defaults.get("cache_max_items", 100)))
        except Exception:
            defaults["cache_max_items"] = 100
        return defaults

    def _save_settings(self) -> None:
        """현재 상태를 설정 파일에 저장"""
        try:
            self.settings["lang_code"] = self._current_language_code()
            self.settings["include_timestamp"] = bool(self.timestamp_var.get())
            self.settings["auto_start"] = bool(self.auto_start_var.get())
            self.settings["cache_max_items"] = max(1, int(self.cache_size_var.get()))
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

        cache_frame = ttk.Frame(option_frame)
        cache_frame.pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(cache_frame, text="캐시 길이(LRU):").pack(side=tk.LEFT)
        self.cache_size_var = tk.IntVar(value=int(self.settings.get("cache_max_items", 100)))
        self.cache_size_spin = ttk.Spinbox(
            cache_frame,
            from_=1,
            to=5000,
            textvariable=self.cache_size_var,
            width=6,
            command=self._on_cache_size_change,
        )
        self.cache_size_spin.pack(side=tk.LEFT, padx=(8, 0))
        self.cache_size_spin.bind("<FocusOut>", self._on_cache_size_change)
        self.cache_size_spin.bind("<Return>", self._on_cache_size_change)

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
        self.status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            foreground="gray",
            wraplength=420,
        )
        self.status_label.pack(fill=tk.X, pady=(0, 8))

        cache_status_frame = ttk.Frame(main_frame)
        cache_status_frame.pack(fill=tk.X, pady=(0, 8))

        self.cache_title_label = ttk.Label(
            cache_status_frame,
            text="캐시 상태 (LRU)",
            font=("Helvetica", 11, "bold"),
        )
        self.cache_title_label.pack(anchor=tk.W, pady=(0, 4))

        self.cache_summary_var = tk.StringVar(value="0 / 0")
        self.cache_summary_label = ttk.Label(
            cache_status_frame,
            textvariable=self.cache_summary_var,
        )
        self.cache_summary_label.pack(anchor=tk.W, padx=8, pady=(0, 2))

        self.cache_progress = ttk.Progressbar(
            cache_status_frame,
            orient=tk.HORIZONTAL,
            mode="determinate",
            length=CACHE_GRAPH_WIDTH,
        )
        self.cache_progress.pack(fill=tk.X, padx=8, pady=(0, 6))

        self.cache_graph = tk.Canvas(
            cache_status_frame,
            width=CACHE_GRAPH_WIDTH,
            height=CACHE_GRAPH_HEIGHT,
            bg="#f6f6f6",
            highlightthickness=1,
            highlightbackground="#d5d5d5",
        )
        self.cache_graph.pack(fill=tk.X, padx=8, pady=(0, 8))

        ttk.Label(
            main_frame,
            text="최근 처리 내역 (최신순)",
            font=("Helvetica", 11, "bold"),
        ).pack(anchor=tk.W)

        history_frame = ttk.Frame(main_frame)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.history_list = tk.Listbox(history_frame, height=12, activestyle="none")
        self.history_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.history_list.bind("<Motion>", self._on_history_hover)
        self.history_list.bind("<Leave>", self._hide_history_tooltip)

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

    def _normalize_geometry(self, geometry: str) -> str:
        """저장된 창 크기가 작으면 최소 크기로 보정."""
        try:
            size, *pos = geometry.split("+")
            width_str, height_str = size.split("x")
            width = max(MIN_WINDOW_WIDTH, int(width_str))
            height = max(MIN_WINDOW_HEIGHT, int(height_str))
            if len(pos) >= 2:
                return f"{width}x{height}+{pos[0]}+{pos[1]}"
            return f"{width}x{height}"
        except Exception:
            return f"{MIN_WINDOW_WIDTH}x{MIN_WINDOW_HEIGHT}"

    def _on_language_change(self, event=None):
        """언어 선택 변경 시"""
        code = self._current_language_code()
        self.fetcher.set_language(code)
        self._invalidate_runtime_cache()
        self._save_settings()
        if self.menubar:
            self.menubar.update_language(code)
        suffix = " (다음 URL부터 적용)" if self.is_running else ""
        self._update_status(f"언어 변경: {code}{suffix} / 캐시 초기화")

    def _on_timestamp_change(self):
        """타임스탬프 옵션 변경 시"""
        include = self.timestamp_var.get()
        self.fetcher.set_timestamp(include)
        self._invalidate_runtime_cache()
        self._save_settings()
        if self.menubar:
            self.menubar.update_timestamp(include)
        status = "타임스탬프 포함" if include else "타임스탬프 제외"
        if self.is_running:
            status = f"{status} (다음 URL부터 적용)"
        self._update_status(f"{status} / 캐시 초기화")

    def _on_auto_start_change(self):
        """자동 시작 옵션 변경 시"""
        self._save_settings()
        enabled = self.auto_start_var.get()
        status = "자동 시작: 켜짐" if enabled else "자동 시작: 꺼짐"
        self._update_status(status)

    def _on_cache_size_change(self, event=None):
        """LRU 캐시 최대 길이 변경 시"""
        del event
        try:
            value = max(1, int(self.cache_size_var.get()))
        except Exception:
            value = int(self.settings.get("cache_max_items", 100))
        self.cache_size_var.set(value)
        self.cache.set_max_items(value)
        self._save_settings()
        self._refresh_cache_status()
        self._update_status(f"캐시 길이 변경: {value}")

    def _invalidate_runtime_cache(self) -> None:
        """언어/타임스탬프 변경 시 런타임 캐시 초기화"""
        self.monitor.reset_processed()
        self.cache.clear_all()
        self._refresh_cache_status()

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
        if self.menubar:
            self.menubar.update_running(True)

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
        if self.menubar:
            self.menubar.update_running(False)

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
        item = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "status": "성공" if success else "실패",
            "video_id": video_id,
            "detail": detail,
        }
        self.recent_history.insert(0, item)
        self.recent_history = self.recent_history[:MAX_HISTORY_ITEMS]
        self._refresh_history_ui()
        self._refresh_cache_status()
        self._save_settings()

    def _refresh_history_ui(self):
        """최근 처리 내역 화면 갱신"""
        self.history_list.delete(0, tk.END)
        for item in self.recent_history:
            detail = item.get("detail", "")
            if len(detail) > 40:
                detail = f"{detail[:37]}..."
            video_id = item.get("video_id", "-")
            video_display = f"{video_id[:8]}..." if len(video_id) > 8 else video_id
            line = (
                f"{item.get('time', '--:--:--')} | "
                f"{item.get('status', '-')} | "
                f"{video_display} | "
                f"{detail}"
            )
            self.history_list.insert(tk.END, line)

    def _on_history_hover(self, event):
        """히스토리 행 hover 시 detail 전체 툴팁 표시"""
        row = self.history_list.nearest(event.y)
        if row < 0 or row >= len(self.recent_history):
            self._hide_history_tooltip()
            return

        if self._history_tooltip and self._history_tooltip_row == row:
            self._move_history_tooltip(event.x_root + 12, event.y_root + 12)
            return

        self._hide_history_tooltip()
        detail = self.recent_history[row].get("detail", "")
        if not detail:
            return

        tooltip = tk.Toplevel(self.root)
        tooltip.wm_overrideredirect(True)
        tooltip.attributes("-topmost", True)
        frame = tk.Frame(
            tooltip,
            background="#fffde8",
            relief=tk.SOLID,
            borderwidth=1,
            padx=10,
            pady=8,
        )
        frame.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(
            frame,
            text="상세 결과",
            anchor="w",
            font=("Helvetica", 11, "bold"),
            background="#fffde8",
            foreground="#2f2f2f",
        )
        title.pack(fill=tk.X, pady=(0, 6))

        message = tk.Message(
            frame,
            text=detail,
            width=560,
            justify=tk.LEFT,
            font=("Helvetica", 11),
            background="#fffde8",
            foreground="#111111",
        )
        message.pack(fill=tk.BOTH, expand=True)
        self._history_tooltip = tooltip
        self._history_tooltip_row = row
        self._move_history_tooltip(event.x_root + 12, event.y_root + 12)

    def _move_history_tooltip(self, x: int, y: int):
        if self._history_tooltip:
            self._history_tooltip.geometry(f"+{x}+{y}")

    def _hide_history_tooltip(self, event=None):
        del event
        if self._history_tooltip:
            self._history_tooltip.destroy()
            self._history_tooltip = None
            self._history_tooltip_row = None

    def _clear_history(self):
        """최근 처리 내역 초기화"""
        self._hide_history_tooltip()
        self.recent_history.clear()
        self._refresh_history_ui()
        self._save_settings()
        self._update_status("최근 처리 내역을 비웠습니다")

    def _refresh_cache_status(self):
        stats = self.cache.stats()
        item_count = stats.get("item_count", 0)
        max_items = stats.get("max_items", 1)
        total_lines = stats.get("total_lines", 0)
        total_bytes = stats.get("total_bytes", 0)
        utilization = stats.get("utilization_pct", 0)

        kb = total_bytes / 1024 if total_bytes else 0.0
        self.cache_summary_var.set(
            f"{item_count} / {max_items} 항목  |  활용률 {utilization}%  |  총 {total_lines}줄  |  {kb:.1f} KB"
        )

        self.cache_progress.configure(maximum=max_items, value=item_count)
        self._draw_cache_graph(stats.get("entries_recent", []))

    def _draw_cache_graph(self, entries_recent: list[dict]):
        self.cache_graph.delete("all")
        if not entries_recent:
            self.cache_graph.create_text(
                CACHE_GRAPH_WIDTH / 2,
                CACHE_GRAPH_HEIGHT / 2,
                text="캐시 데이터 없음",
                fill="#7a7a7a",
                font=("Helvetica", 10),
            )
            return

        bars = entries_recent[:8]
        max_lines = max(max(1, int(item.get("line_count", 0))) for item in bars)
        slot = CACHE_GRAPH_WIDTH / len(bars)
        for idx, item in enumerate(bars):
            lines = max(1, int(item.get("line_count", 0)))
            x0 = idx * slot + 8
            x1 = (idx + 1) * slot - 8
            h = int((lines / max_lines) * (CACHE_GRAPH_HEIGHT - 26))
            y1 = CACHE_GRAPH_HEIGHT - 8
            y0 = y1 - h

            lang = str(item.get("lang_code", "auto"))
            ts_on = bool(item.get("include_timestamp", False))
            color = "#2878c8" if not ts_on else "#4f9d69"
            if lang.startswith("en"):
                color = "#c86f28" if not ts_on else "#bf8b31"

            self.cache_graph.create_rectangle(x0, y0, x1, y1, fill=color, width=0)
            video_id = str(item.get("video_id", ""))
            short_id = f"{video_id[:4]}…" if len(video_id) > 4 else video_id
            self.cache_graph.create_text(
                (x0 + x1) / 2,
                CACHE_GRAPH_HEIGHT - 2,
                text=short_id,
                fill="#505050",
                font=("Helvetica", 8),
                anchor="s",
            )

    # ── menubar ──

    def _setup_menubar(self):
        """MenuBarController 생성 + Dock 아이콘 숨김"""
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        from menubar import MenuBarController

        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory
        )

        self.menubar = MenuBarController(
            on_toggle=self._toggle_monitor,
            on_language=self._menubar_on_language,
            on_timestamp=self._menubar_on_timestamp,
            on_show_settings=self._show_window,
            on_quit=self._on_close,
            initial_lang=self._current_language_code(),
            initial_timestamp=self.timestamp_var.get(),
            initial_running=self.is_running,
        )

    def _on_window_close(self):
        """창 닫기(빨간 X) → 숨김 (종료 아님)"""
        self.root.withdraw()

    def _show_window(self):
        """메뉴바에서 '설정 열기' → 창 재표시 + 포커스"""
        from AppKit import NSApplication

        self.root.deiconify()
        self.root.lift()
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def _menubar_on_language(self, code: str):
        """메뉴바 언어 선택 → tkinter 변수 갱신 → 기존 핸들러 호출"""
        label = self.code_to_label.get(code)
        if label:
            self.lang_var.set(label)
            self._on_language_change()

    def _menubar_on_timestamp(self):
        """메뉴바 타임스탬프 토글 → tkinter 변수 반전 → 기존 핸들러 호출"""
        self.timestamp_var.set(not self.timestamp_var.get())
        self._on_timestamp_change()

    # ── lifecycle ──

    def _on_close(self):
        """앱 종료"""
        if self._closing:
            return
        self._closing = True

        try:
            self._hide_history_tooltip()
            self._save_settings()
            self._stop_monitor()
            if self.menubar:
                self.menubar.cleanup()
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
