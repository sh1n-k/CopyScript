from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from copyscript.config.constants import CACHE_GRAPH_HEIGHT
from copyscript.ui import theme


class CachePanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame", padding=12)
        ttk.Label(self, text="캐시 상태", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 6))
        self.summary_var = tk.StringVar(value="0 / 0")
        ttk.Label(self, textvariable=self.summary_var, style="CardBody.TLabel").pack(anchor=tk.W, padx=4, pady=(0, 4))
        self.utilization_bar = tk.Canvas(
            self,
            width=1,
            height=14,
            bg=theme.CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
        )
        self.utilization_bar.pack(fill=tk.X, padx=4, pady=(0, 8))
        self.graph = tk.Canvas(
            self,
            width=1,
            height=CACHE_GRAPH_HEIGHT,
            bg=theme.CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
        )
        self.graph.pack(fill=tk.X, padx=4)
        self.utilization_bar.bind("<Configure>", self._handle_resize)
        self.graph.bind("<Configure>", self._handle_resize)
        self._entries_recent: list[dict] = []
        self._utilization_pct = 0

    def refresh(self, stats: dict) -> None:
        item_count = stats.get("item_count", 0)
        max_items = stats.get("max_items", 1)
        total_lines = stats.get("total_lines", 0)
        total_bytes = stats.get("total_bytes", 0)
        utilization = stats.get("utilization_pct", 0)
        kb = total_bytes / 1024 if total_bytes else 0.0
        self.summary_var.set(
            f"{item_count} / {max_items} 항목  |  활용률 {utilization}%  |  총 {total_lines}줄  |  {kb:.1f} KB"
        )
        self._utilization_pct = max(0, min(100, int(utilization)))
        self._draw_utilization_bar()
        self._entries_recent = list(stats.get("entries_recent", []))
        self._draw_graph(self._entries_recent)

    def _handle_resize(self, event=None) -> None:
        del event
        self._draw_utilization_bar()
        self._draw_graph(self._entries_recent)

    def _draw_utilization_bar(self) -> None:
        self.utilization_bar.delete("all")
        width = max(40, self.utilization_bar.winfo_width())
        height = max(10, self.utilization_bar.winfo_height())
        inset = 2
        fill_width = int((width - inset * 2) * (self._utilization_pct / 100))
        self.utilization_bar.create_rectangle(
            inset,
            inset,
            width - inset,
            height - inset,
            fill=theme.CARD,
            outline="",
        )
        if fill_width > 0:
            self.utilization_bar.create_rectangle(
                inset,
                inset,
                inset + fill_width,
                height - inset,
                fill=theme.ACCENT,
                outline="",
            )

    def _draw_graph(self, entries_recent: list[dict]) -> None:
        self.graph.delete("all")
        width = max(80, self.graph.winfo_width())
        height = max(24, self.graph.winfo_height())
        if not entries_recent:
            self.graph.create_text(
                width / 2,
                height / 2,
                text="캐시 데이터 없음",
                fill=theme.MUTED,
                font=theme.SMALL_FONT,
            )
            return
        bars = entries_recent[:8]
        max_lines = max(max(1, int(item.get("line_count", 0))) for item in bars)
        slot = width / len(bars)
        for index, item in enumerate(bars):
            lines = max(1, int(item.get("line_count", 0)))
            x0 = index * slot + 8
            x1 = (index + 1) * slot - 8
            bar_height = int((lines / max_lines) * max(12, height - 26))
            y1 = height - 8
            y0 = y1 - bar_height
            lang = str(item.get("lang_code", "auto"))
            timestamp_enabled = bool(item.get("include_timestamp", False))
            color = theme.ACCENT if not timestamp_enabled else theme.SUCCESS
            if lang.startswith("en"):
                color = theme.ACCENT_ALT if not timestamp_enabled else "#b28b44"
            self.graph.create_rectangle(x0, y0, x1, y1, fill=color, width=0)
            video_id = str(item.get("video_id", ""))
            label = f"{video_id[:4]}..." if len(video_id) > 4 else video_id
            self.graph.create_text(
                (x0 + x1) / 2,
                height - 2,
                text=label,
                fill=theme.TEXT,
                font=theme.SMALL_FONT,
                anchor="s",
            )
