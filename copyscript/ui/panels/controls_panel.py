from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ControlsPanel(ttk.Frame):
    def __init__(self, parent, *, on_toggle, on_clear, on_quit):
        super().__init__(parent, style="Root.TFrame")
        self.toggle_button = ttk.Button(self, text="▶ 시작", command=on_toggle, width=12, style="Primary.TButton")
        self.toggle_button.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(self, text="내역 지우기", command=on_clear, width=12).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(self, text="종료", command=on_quit, width=12).pack(side=tk.LEFT)

    def set_running(self, is_running: bool) -> None:
        self.toggle_button.config(text="⏹ 정지" if is_running else "▶ 시작")
