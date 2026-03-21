from __future__ import annotations

import platform
from typing import Callable

from copyscript.config.languages import SUPPORTED_LANGUAGES
from copyscript.platform.app_paths import get_icon_path

if platform.system() != "Windows":
    raise ImportError("tray module is Windows-only")

from PIL import Image, ImageDraw
import pystray


class TrayController:
    def __init__(
        self,
        *,
        on_toggle: Callable[[], None],
        on_language: Callable[[str], None],
        on_timestamp: Callable[[], None],
        on_show_settings: Callable[[], None],
        on_quit: Callable[[], None],
        initial_lang: str = "ko",
        initial_timestamp: bool = False,
        initial_running: bool = False,
    ):
        self._callbacks = {
            "on_toggle": on_toggle,
            "on_language": on_language,
            "on_timestamp": on_timestamp,
            "on_show_settings": on_show_settings,
            "on_quit": on_quit,
        }
        self._lang_code = initial_lang
        self._include_timestamp = initial_timestamp
        self._is_running = initial_running
        self._icon = pystray.Icon(
            "CopyScript",
            self._load_icon_image(),
            "CopyScript",
            menu=self._build_menu(),
        )
        self._icon.run_detached()

    def update_running(self, is_running: bool) -> None:
        self._is_running = is_running
        self._icon.update_menu()

    def update_language(self, lang_code: str) -> None:
        self._lang_code = lang_code
        self._icon.update_menu()

    def update_timestamp(self, include: bool) -> None:
        self._include_timestamp = include
        self._icon.update_menu()

    def cleanup(self) -> None:
        self._icon.stop()

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._toggle_text, self._handle_toggle),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("언어", self._build_language_menu()),
            pystray.MenuItem(
                "타임스탬프 포함",
                self._handle_timestamp,
                checked=lambda item: self._include_timestamp,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("설정 열기", self._handle_show_settings, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._handle_quit),
        )

    def _build_language_menu(self) -> pystray.Menu:
        return pystray.Menu(
            *[
                self._build_language_item(name, code)
                for name, code in SUPPORTED_LANGUAGES
            ]
        )

    def _build_language_item(self, name: str, code: str) -> pystray.MenuItem:
        return pystray.MenuItem(
            f"{name} ({code})",
            self._build_language_action(code),
            checked=self._build_language_checked(code),
            radio=True,
        )

    def _build_language_action(self, code: str):
        def _action(icon, item) -> None:
            del icon, item
            self._callbacks["on_language"](code)

        return _action

    def _build_language_checked(self, code: str):
        def _checked(item) -> bool:
            del item
            return self._lang_code == code

        return _checked

    def _load_icon_image(self) -> Image.Image:
        icon_path = get_icon_path()
        if icon_path.exists():
            return Image.open(icon_path)
        return self._draw_fallback_icon()

    def _draw_fallback_icon(self) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (29, 53, 87, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=14, fill=(244, 162, 97, 255))
        draw.rounded_rectangle((12, 12, 52, 52), radius=10, fill=(29, 53, 87, 255))
        draw.rectangle((18, 22, 28, 42), fill=(244, 162, 97, 255))
        draw.pieslice((30, 18, 50, 46), start=40, end=320, fill=(244, 162, 97, 255))
        draw.rectangle((30, 30, 40, 42), fill=(29, 53, 87, 255))
        return image

    def _status_text(self, item) -> str:
        del item
        return "상태: 모니터링 중" if self._is_running else "상태: 정지됨"

    def _toggle_text(self, item) -> str:
        del item
        return "\u23f9 정지" if self._is_running else "\u25b6 시작"

    def _handle_toggle(self, icon, item) -> None:
        del icon, item
        self._callbacks["on_toggle"]()

    def _handle_timestamp(self, icon, item) -> None:
        del icon, item
        self._callbacks["on_timestamp"]()

    def _handle_show_settings(self, icon, item) -> None:
        del icon, item
        self._callbacks["on_show_settings"]()

    def _handle_quit(self, icon, item) -> None:
        del icon, item
        self._callbacks["on_quit"]()
