from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from copyscript.config.models import HistoryEntry
from copyscript.ui import theme


class HistoryPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Root.TFrame")
        ttk.Label(self, text="최근 처리 내역 (최신순)", style="Body.TLabel").pack(anchor=tk.W)
        frame = ttk.Frame(self, style="Root.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.listbox = tk.Listbox(
            frame,
            height=12,
            activestyle="none",
            bg=theme.CARD,
            fg=theme.TEXT,
            selectbackground=theme.CARD_ALT,
            selectforeground=theme.TEXT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            relief=tk.FLAT,
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<Motion>", self._on_hover)
        self.listbox.bind("<Leave>", self.hide_tooltip)
        self._tooltip: tk.Toplevel | None = None
        self._tooltip_row: int | None = None
        self._items: list[HistoryEntry] = []

    def set_items(self, items: list[HistoryEntry]) -> None:
        self._items = items
        self.listbox.delete(0, tk.END)
        for item in items:
            detail = item.detail if len(item.detail) <= 40 else f"{item.detail[:37]}..."
            video_display = f"{item.video_id[:8]}..." if len(item.video_id) > 8 else item.video_id
            line = f"{item.time or '--:--:--'} | {item.status or '-'} | {video_display or '-'} | {detail}"
            self.listbox.insert(tk.END, line)

    def hide_tooltip(self, event=None) -> None:
        del event
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None
            self._tooltip_row = None

    def _on_hover(self, event) -> None:
        row = self.listbox.nearest(event.y)
        if row < 0 or row >= len(self._items):
            self.hide_tooltip()
            return
        if self._tooltip and self._tooltip_row == row:
            self._move_tooltip(event.x_root + 12, event.y_root + 12)
            return
        self.hide_tooltip()
        detail = self._items[row].detail
        if not detail:
            return
        tooltip = tk.Toplevel(self)
        tooltip.wm_overrideredirect(True)
        tooltip.attributes("-topmost", True)
        frame = tk.Frame(
            tooltip,
            background=theme.CARD_ALT,
            relief=tk.SOLID,
            borderwidth=1,
            padx=10,
            pady=8,
        )
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            frame,
            text="상세 결과",
            anchor="w",
            font=theme.TITLE_FONT,
            background=theme.CARD_ALT,
            foreground=theme.TEXT,
        ).pack(fill=tk.X, pady=(0, 6))
        tk.Message(
            frame,
            text=detail,
            width=560,
            justify=tk.LEFT,
            font=theme.UI_FONT,
            background=theme.CARD_ALT,
            foreground=theme.TEXT,
        ).pack(fill=tk.BOTH, expand=True)
        self._tooltip = tooltip
        self._tooltip_row = row
        self._move_tooltip(event.x_root + 12, event.y_root + 12)

    def _move_tooltip(self, x: int, y: int) -> None:
        if self._tooltip:
            self._tooltip.geometry(f"+{x}+{y}")
