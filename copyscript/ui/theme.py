from __future__ import annotations

from tkinter import ttk

SURFACE = "#f5f2ea"
CARD = "#fbf9f3"
CARD_ALT = "#efe7d7"
TEXT = "#1f1d18"
MUTED = "#6b665c"
SUCCESS = "#2f7d4f"
ERROR = "#b14331"
ACCENT = "#255f85"
ACCENT_ALT = "#ad6c2f"
BORDER = "#d8ccb8"

UI_FONT = ("Helvetica", 11)
TITLE_FONT = ("Helvetica", 11, "bold")
SMALL_FONT = ("Helvetica", 9)


def apply_theme(style: ttk.Style) -> None:
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Root.TFrame", background=SURFACE)
    style.configure("Card.TFrame", background=CARD, relief="flat")
    style.configure("Title.TLabel", background=CARD, foreground=TEXT, font=TITLE_FONT)
    style.configure("Body.TLabel", background=SURFACE, foreground=TEXT, font=UI_FONT)
    style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=UI_FONT)
    style.configure("CardBody.TLabel", background=CARD, foreground=TEXT, font=UI_FONT)
    style.configure("Hint.TLabel", background=SURFACE, foreground=MUTED, font=SMALL_FONT)
    style.configure("Primary.TButton", font=UI_FONT)
    style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, font=UI_FONT)
    style.configure("TCombobox", font=UI_FONT)
    style.configure("TSpinbox", font=UI_FONT)
    style.configure("TProgressbar", thickness=10)
