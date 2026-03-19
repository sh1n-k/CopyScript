from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from copyscript.config.constants import CACHE_GRAPH_HEIGHT, CACHE_GRAPH_WIDTH
from copyscript.ui import theme


class CachePanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame", padding=12)
        ttk.Label(self, text="캐시 상태 (LRU)", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 4))
        self.summary_var = tk.StringVar(value="0 / 0")
        ttk.Label(self, textvariable=self.summary_var, style="CardBody.TLabel").pack(anchor=tk.W, padx=4, pady=(0, 4))
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode="determinate", length=CACHE_GRAPH_WIDTH)
        self.progress.pack(fill=tk.X, padx=4, pady=(0, 8))
        self.graph = tk.Canvas(
            self,
            width=CACHE_GRAPH_WIDTH,
            height=CACHE_GRAPH_HEIGHT,
            bg=theme.CARD_ALT,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
        )
        self.graph.pack(fill=tk.X, padx=4)

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
        self.progress.configure(maximum=max_items, value=item_count)
        self._draw_graph(stats.get("entries_recent", []))

    def _draw_graph(self, entries_recent: list[dict]) -> None:
        self.graph.delete("all")
        if not entries_recent:
            self.graph.create_text(
                CACHE_GRAPH_WIDTH / 2,
                CACHE_GRAPH_HEIGHT / 2,
                text="캐시 데이터 없음",
                fill=theme.MUTED,
                font=theme.SMALL_FONT,
            )
            return
        bars = entries_recent[:8]
        max_lines = max(max(1, int(item.get("line_count", 0))) for item in bars)
        slot = CACHE_GRAPH_WIDTH / len(bars)
        for index, item in enumerate(bars):
            lines = max(1, int(item.get("line_count", 0)))
            x0 = index * slot + 8
            x1 = (index + 1) * slot - 8
            height = int((lines / max_lines) * (CACHE_GRAPH_HEIGHT - 26))
            y1 = CACHE_GRAPH_HEIGHT - 8
            y0 = y1 - height
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
                CACHE_GRAPH_HEIGHT - 2,
                text=label,
                fill=theme.TEXT,
                font=theme.SMALL_FONT,
                anchor="s",
            )
