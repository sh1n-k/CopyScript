from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from copyscript.ui import theme


class StatusPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Root.TFrame")
        ttk.Label(
            self,
            text="옵션 변경은 즉시 저장되며, 모니터링 중에는 다음 URL부터 적용됩니다.",
            style="Hint.TLabel",
        ).pack(fill=tk.X, pady=(0, 8))
        self.status_var = tk.StringVar(value="시작 버튼을 누른 뒤 YouTube URL을 복사하세요")
        self.status_label = ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", wraplength=420)
        self.status_label.pack(fill=tk.X)

    def set_status(self, status: str, is_error: bool = False) -> None:
        self.status_var.set(status)
        color = theme.ERROR if is_error else (theme.SUCCESS if "완료" in status else theme.MUTED)
        self.status_label.configure(foreground=color)
