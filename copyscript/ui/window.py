from __future__ import annotations

import importlib
import platform
import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any
from typing import Callable

from copyscript.app.controller import AppController
from copyscript.app.runtime_options import RuntimeOptions
from copyscript.config.constants import DEFAULT_GEOMETRY, MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH
from copyscript.platform.app_paths import get_icon_path
from copyscript.ui.panels import CachePanel, HistoryPanel, SettingsPanel, StatusPanel
from copyscript.ui.theme import apply_theme

IS_MACOS = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"


def should_hide_on_start(system_name: str, start_hidden: bool) -> bool:
    if system_name == "Darwin":
        return True
    return system_name == "Windows" and start_hidden


class AppWindow:
    def __init__(self, runtime_options: RuntimeOptions | None = None):
        self.runtime_options = runtime_options or RuntimeOptions()
        self.controller = AppController()
        self.root = tk.Tk()
        self._ui_thread_id = threading.get_ident()
        self._ui_action_queue: queue.Queue[tuple[Callable[..., None], tuple[Any, ...]]] | None = None
        self.root.title("CopyScript")
        self.root.geometry(DEFAULT_GEOMETRY)
        self.root.resizable(False, False)
        self.root.configure(background="#f5f2ea")
        apply_theme(ttk.Style(self.root))
        self._configure_window_icon()
        if IS_WINDOWS:
            self._ui_action_queue = queue.Queue()
            self.root.after(50, self._drain_ui_actions)

        saved_geometry = self.controller.settings.window_geometry
        if saved_geometry:
            self.root.geometry(self._normalize_geometry(saved_geometry))
        self._start_hidden = should_hide_on_start(platform.system(), self.runtime_options.start_hidden)
        if self._start_hidden:
            self.root.withdraw()

        self.status_ui = None
        self._build_ui()
        self.controller.bind(
            on_status=self._queue_status,
            on_history=self._queue_history,
            on_cache=self._queue_cache,
            on_running=self._queue_running,
        )
        self.controller.publish_initial_state()
        if not saved_geometry:
            self._center_window()
        if IS_MACOS:
            self._setup_menubar()
            self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        elif IS_WINDOWS:
            self._setup_tray()
            self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        else:
            self.root.protocol("WM_DELETE_WINDOW", self._quit)
        if self.controller.settings.monitor_on_launch:
            self.root.after(120, self.controller.start_monitoring)

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=14, style="Root.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.settings_panel = SettingsPanel(
            main_frame,
            settings=self.controller.settings,
            on_language_change=self._on_language_change,
            on_timestamp_change=self._on_timestamp_change,
            on_monitor_on_launch_change=self.controller.update_monitor_on_launch,
            on_launch_at_login_change=self._on_launch_at_login_change,
            on_cache_size_change=self.controller.update_cache_size,
            on_toggle=self.controller.toggle_monitoring,
            on_clear=self._clear_history,
            on_quit=self._quit,
        )
        self.settings_panel.pack(fill=tk.X, pady=(0, 8))
        self.status_panel = StatusPanel(main_frame)
        self.status_panel.pack(fill=tk.X, pady=(0, 8))
        self.cache_panel = CachePanel(main_frame)
        self.cache_panel.pack(fill=tk.X, pady=(0, 8))
        self.history_panel = HistoryPanel(main_frame)
        self.history_panel.pack(fill=tk.BOTH, expand=True)

    def _on_language_change(self, code: str) -> None:
        self.controller.update_language(code)
        if self.status_ui:
            self.status_ui.update_language(code)

    def _on_timestamp_change(self, include: bool) -> None:
        self.controller.update_timestamp(include)
        if self.status_ui:
            self.status_ui.update_timestamp(include)

    def _on_launch_at_login_change(self, enabled: bool) -> None:
        self.controller.update_launch_at_login(enabled)
        self.settings_panel.set_launch_at_login(self.controller.settings.launch_at_login)

    def _clear_history(self) -> None:
        self.history_panel.hide_tooltip()
        self.controller.clear_history()

    def _queue_status(self, status: str, is_error: bool) -> None:
        self._run_on_ui_thread(self.status_panel.set_status, status, is_error)

    def _queue_history(self, items) -> None:
        self._run_on_ui_thread(self.history_panel.set_items, items)

    def _queue_cache(self, stats: dict) -> None:
        self._run_on_ui_thread(self.cache_panel.refresh, stats)

    def _queue_running(self, is_running: bool) -> None:
        self._run_on_ui_thread(self._apply_running_state, is_running)

    def _apply_running_state(self, is_running: bool) -> None:
        self.settings_panel.set_running(is_running)
        if self.status_ui:
            self.status_ui.update_running(is_running)

    def _normalize_geometry(self, geometry: str) -> str:
        try:
            size, *position = geometry.split("+")
            width_str, height_str = size.split("x")
            width = max(MIN_WINDOW_WIDTH, int(width_str))
            height = max(MIN_WINDOW_HEIGHT, int(height_str))
            if len(position) >= 2:
                return f"{width}x{height}+{position[0]}+{position[1]}"
            return f"{width}x{height}"
        except Exception:
            return f"{MIN_WINDOW_WIDTH}x{MIN_WINDOW_HEIGHT}"

    def _center_window(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_menubar(self) -> None:
        from copyscript.platform.menubar import MenuBarController

        appkit = importlib.import_module("AppKit")
        ns_application = appkit.NSApplication
        activation_policy = appkit.NSApplicationActivationPolicyAccessory
        ns_application.sharedApplication().setActivationPolicy_(activation_policy)
        self.status_ui = MenuBarController(
            on_toggle=self.controller.toggle_monitoring,
            on_language=self._menubar_on_language,
            on_timestamp=self._menubar_on_timestamp,
            on_show_settings=self._show_window,
            on_quit=self._quit,
            initial_lang=self.controller.settings.lang_code,
            initial_timestamp=self.controller.settings.include_timestamp,
            initial_running=self.controller.is_running,
        )

    def _setup_tray(self) -> None:
        from copyscript.platform.tray import TrayController

        self.status_ui = TrayController(
            on_toggle=lambda: self._run_on_ui_thread(self.controller.toggle_monitoring),
            on_language=lambda code: self._run_on_ui_thread(self._tray_on_language, code),
            on_timestamp=lambda: self._run_on_ui_thread(self._tray_on_timestamp),
            on_show_settings=lambda: self._run_on_ui_thread(self._show_window),
            on_quit=lambda: self._run_on_ui_thread(self._quit),
            initial_lang=self.controller.settings.lang_code,
            initial_timestamp=self.controller.settings.include_timestamp,
            initial_running=self.controller.is_running,
        )

    def _menubar_on_language(self, code: str) -> None:
        self.settings_panel.set_language_code(code)
        self._on_language_change(code)

    def _menubar_on_timestamp(self) -> None:
        include = not self.settings_panel.timestamp_var.get()
        self.settings_panel.set_timestamp(include)
        self._on_timestamp_change(include)

    def _tray_on_language(self, code: str) -> None:
        self.settings_panel.set_language_code(code)
        self._on_language_change(code)

    def _tray_on_timestamp(self) -> None:
        include = not self.settings_panel.timestamp_var.get()
        self.settings_panel.set_timestamp(include)
        self._on_timestamp_change(include)

    def _on_window_close(self) -> None:
        self.history_panel.hide_tooltip()
        self.root.withdraw()

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        if IS_MACOS:
            appkit = importlib.import_module("AppKit")
            appkit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            return
        self.root.focus_force()

    def _quit(self) -> None:
        self.history_panel.hide_tooltip()
        self.controller.shutdown(self.root.geometry())
        if self.status_ui:
            self.status_ui.cleanup()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()

    def _drain_ui_actions(self) -> None:
        if not self.root.winfo_exists():
            return
        if self._ui_action_queue is not None:
            while True:
                try:
                    callback, args = self._ui_action_queue.get_nowait()
                except queue.Empty:
                    break
                callback(*args)
        self.root.after(50, self._drain_ui_actions)

    def _run_on_ui_thread(self, callback, *args) -> None:
        if IS_WINDOWS and threading.get_ident() != self._ui_thread_id:
            if self._ui_action_queue is not None:
                self._ui_action_queue.put((callback, args))
            return
        if self.root.winfo_exists():
            callback(*args)

    def _configure_window_icon(self) -> None:
        if not IS_WINDOWS:
            return
        icon_path = get_icon_path()
        if not icon_path.exists():
            return
        try:
            self.root.iconbitmap(default=str(icon_path))
        except Exception:
            pass
