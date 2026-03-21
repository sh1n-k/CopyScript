from __future__ import annotations

import importlib
import platform
import tkinter as tk
from tkinter import ttk

from copyscript.app.controller import AppController
from copyscript.config.constants import DEFAULT_GEOMETRY, MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH
from copyscript.ui.panels import CachePanel, HistoryPanel, SettingsPanel, StatusPanel
from copyscript.ui.theme import apply_theme

IS_MACOS = platform.system() == "Darwin"


class AppWindow:
    def __init__(self):
        self.controller = AppController()
        self.root = tk.Tk()
        self.root.title("CopyScript")
        self.root.geometry(DEFAULT_GEOMETRY)
        self.root.resizable(False, False)
        self.root.configure(background="#f5f2ea")
        apply_theme(ttk.Style(self.root))

        saved_geometry = self.controller.settings.window_geometry
        if saved_geometry:
            self.root.geometry(self._normalize_geometry(saved_geometry))
        if IS_MACOS:
            self.root.withdraw()

        self.menubar = None
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
        else:
            self.root.protocol("WM_DELETE_WINDOW", self._quit)
        if self.controller.settings.auto_start:
            self.root.after(120, self.controller.start_monitoring)

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=14, style="Root.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.settings_panel = SettingsPanel(
            main_frame,
            settings=self.controller.settings,
            on_language_change=self._on_language_change,
            on_timestamp_change=self._on_timestamp_change,
            on_auto_start_change=self.controller.update_auto_start,
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
        if self.menubar:
            self.menubar.update_language(code)

    def _on_timestamp_change(self, include: bool) -> None:
        self.controller.update_timestamp(include)
        if self.menubar:
            self.menubar.update_timestamp(include)

    def _clear_history(self) -> None:
        self.history_panel.hide_tooltip()
        self.controller.clear_history()

    def _queue_status(self, status: str, is_error: bool) -> None:
        if self.root.winfo_exists():
            self.root.after(0, lambda: self.status_panel.set_status(status, is_error))

    def _queue_history(self, items) -> None:
        if self.root.winfo_exists():
            self.root.after(0, lambda: self.history_panel.set_items(items))

    def _queue_cache(self, stats: dict) -> None:
        if self.root.winfo_exists():
            self.root.after(0, lambda: self.cache_panel.refresh(stats))

    def _queue_running(self, is_running: bool) -> None:
        if self.root.winfo_exists():
            self.root.after(0, lambda: self._apply_running_state(is_running))

    def _apply_running_state(self, is_running: bool) -> None:
        self.settings_panel.set_running(is_running)
        if self.menubar:
            self.menubar.update_running(is_running)

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
        self.menubar = MenuBarController(
            on_toggle=self.controller.toggle_monitoring,
            on_language=self._menubar_on_language,
            on_timestamp=self._menubar_on_timestamp,
            on_show_settings=self._show_window,
            on_quit=self._quit,
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

    def _on_window_close(self) -> None:
        self.history_panel.hide_tooltip()
        self.root.withdraw()

    def _show_window(self) -> None:
        appkit = importlib.import_module("AppKit")
        self.root.deiconify()
        self.root.lift()
        appkit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def _quit(self) -> None:
        self.history_panel.hide_tooltip()
        self.controller.shutdown(self.root.geometry())
        if self.menubar:
            self.menubar.cleanup()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
