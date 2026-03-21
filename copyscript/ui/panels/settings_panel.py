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
        on_toggle,
        on_clear,
        on_quit,
    ):
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.labels, self.label_to_code, self.code_to_label = build_language_maps()
        self._on_language_change = on_language_change
        self._on_timestamp_change = on_timestamp_change
        self._on_auto_start_change = on_auto_start_change
        self._on_cache_size_change = on_cache_size_change

        ttk.Label(self, text="사용자 설정 및 제어", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 8))

        form = ttk.Frame(self, style="Card.TFrame")
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="언어", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))

        initial_lang = self.code_to_label.get(settings.lang_code, self.labels[0])
        self.lang_var = tk.StringVar(value=initial_lang)
        self.lang_combo = ttk.Combobox(
            form,
            textvariable=self.lang_var,
            values=self.labels,
            state="readonly",
            width=24,
        )
        self.lang_combo.grid(row=0, column=1, sticky="w", pady=(0, 6))
        self.lang_combo.bind("<<ComboboxSelected>>", self._handle_language)

        ttk.Label(form, text="출력 형식", style="CardMuted.TLabel").grid(row=1, column=0, sticky="nw", pady=(0, 6))
        self.timestamp_var = tk.BooleanVar(value=settings.include_timestamp)
        ttk.Checkbutton(
            form,
            text="타임스탬프 포함 [00:00]",
            variable=self.timestamp_var,
            command=self._handle_timestamp,
        ).grid(row=1, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="시작 옵션", style="CardMuted.TLabel").grid(row=2, column=0, sticky="nw", pady=(0, 6))
        self.auto_start_var = tk.BooleanVar(value=settings.auto_start)
        ttk.Checkbutton(
            form,
            text="앱 실행 시 모니터링 자동 시작",
            variable=self.auto_start_var,
            command=self._handle_auto_start,
        ).grid(row=2, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="캐시 길이", style="CardMuted.TLabel").grid(row=3, column=0, sticky="w")
        cache_frame = ttk.Frame(form, style="Card.TFrame")
        cache_frame.grid(row=3, column=1, sticky="w")
        self.cache_size_var = tk.IntVar(value=settings.cache_max_items)
        self.cache_spin = ttk.Spinbox(
            cache_frame,
            from_=1,
            to=5000,
            textvariable=self.cache_size_var,
            width=6,
            command=self._handle_cache_size,
        )
        self.cache_spin.pack(side=tk.LEFT)
        ttk.Label(cache_frame, text="항목", style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(8, 0))
        self.cache_spin.bind("<FocusOut>", self._handle_cache_size)
        self.cache_spin.bind("<Return>", self._handle_cache_size)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(10, 10))
        button_row = ttk.Frame(self, style="Card.TFrame")
        button_row.pack(fill=tk.X)
        self.toggle_button = ttk.Button(button_row, text="▶ 시작", command=on_toggle, width=12, style="Primary.TButton")
        self.toggle_button.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_row, text="내역 지우기", command=on_clear, width=12).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_row, text="종료", command=on_quit, width=12).pack(side=tk.LEFT)

    def set_language_code(self, code: str) -> None:
        label = self.code_to_label.get(code)
        if label:
            self.lang_var.set(label)

    def set_timestamp(self, include: bool) -> None:
        self.timestamp_var.set(include)

    def set_running(self, is_running: bool) -> None:
        self.toggle_button.config(text="⏹ 정지" if is_running else "▶ 시작")

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
