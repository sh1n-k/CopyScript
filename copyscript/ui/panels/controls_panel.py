from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ControlsPanel(ttk.Frame):
    def __init__(self, parent, *, on_toggle, on_clear, on_quit):
        super().__init__(parent, style="Card.TFrame", padding=12)
        ttk.Label(self, text="실행 제어", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(self, text="모니터링과 내역 정리를 바로 실행합니다.", style="CardMuted.TLabel").pack(
            anchor=tk.W, pady=(2, 8)
        )

        button_row = ttk.Frame(self, style="Card.TFrame")
        button_row.pack(fill=tk.X)
        self.toggle_button = ttk.Button(button_row, text="▶ 시작", command=on_toggle, width=12, style="Primary.TButton")
        self.toggle_button.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_row, text="내역 지우기", command=on_clear, width=12).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_row, text="종료", command=on_quit, width=12).pack(side=tk.LEFT)

    def set_running(self, is_running: bool) -> None:
        self.toggle_button.config(text="⏹ 정지" if is_running else "▶ 시작")
