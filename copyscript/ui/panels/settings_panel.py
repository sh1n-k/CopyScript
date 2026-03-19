from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from copyscript.config.languages import build_language_maps
from copyscript.config.models import AppSettings


class SettingsPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        *,
        settings: AppSettings,
        on_language_change,
        on_timestamp_change,
        on_auto_start_change,
        on_cache_size_change,
    ):
        super().__init__(parent, style="Root.TFrame")
        self.labels, self.label_to_code, self.code_to_label = build_language_maps()
        self._on_language_change = on_language_change
        self._on_timestamp_change = on_timestamp_change
        self._on_auto_start_change = on_auto_start_change
        self._on_cache_size_change = on_cache_size_change

        lang_frame = ttk.Frame(self, style="Root.TFrame")
        lang_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(lang_frame, text="언어:", style="Body.TLabel").pack(side=tk.LEFT)

        initial_lang = self.code_to_label.get(settings.lang_code, self.labels[0])
        self.lang_var = tk.StringVar(value=initial_lang)
        self.lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.lang_var,
            values=self.labels,
            state="readonly",
            width=24,
        )
        self.lang_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.lang_combo.bind("<<ComboboxSelected>>", self._handle_language)

        self.timestamp_var = tk.BooleanVar(value=settings.include_timestamp)
        ttk.Checkbutton(
            self,
            text="타임스탬프 포함 [00:00]",
            variable=self.timestamp_var,
            command=self._handle_timestamp,
        ).pack(anchor=tk.W)

        self.auto_start_var = tk.BooleanVar(value=settings.auto_start)
        ttk.Checkbutton(
            self,
            text="앱 실행 시 모니터링 자동 시작",
            variable=self.auto_start_var,
            command=self._handle_auto_start,
        ).pack(anchor=tk.W)

        cache_frame = ttk.Frame(self, style="Root.TFrame")
        cache_frame.pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(cache_frame, text="캐시 길이(LRU):", style="Body.TLabel").pack(side=tk.LEFT)
        self.cache_size_var = tk.IntVar(value=settings.cache_max_items)
        self.cache_spin = ttk.Spinbox(
            cache_frame,
            from_=1,
            to=5000,
            textvariable=self.cache_size_var,
            width=6,
            command=self._handle_cache_size,
        )
        self.cache_spin.pack(side=tk.LEFT, padx=(8, 0))
        self.cache_spin.bind("<FocusOut>", self._handle_cache_size)
        self.cache_spin.bind("<Return>", self._handle_cache_size)

    def set_language_code(self, code: str) -> None:
        label = self.code_to_label.get(code)
        if label:
            self.lang_var.set(label)

    def set_timestamp(self, include: bool) -> None:
        self.timestamp_var.set(include)

    def _current_language_code(self) -> str:
        selected = self.lang_combo.get()
        code = self.label_to_code.get(selected)
        if code:
            return code
        if "(" in selected and selected.endswith(")"):
            return selected.split("(")[-1].rstrip(")")
        return "ko"

    def _handle_language(self, event=None) -> None:
        del event
        self._on_language_change(self._current_language_code())

    def _handle_timestamp(self) -> None:
        self._on_timestamp_change(bool(self.timestamp_var.get()))

    def _handle_auto_start(self) -> None:
        self._on_auto_start_change(bool(self.auto_start_var.get()))

    def _handle_cache_size(self, event=None) -> None:
        del event
        try:
            value = max(1, int(self.cache_size_var.get()))
        except Exception:
            value = 100
        self.cache_size_var.set(value)
        self._on_cache_size_change(value)
