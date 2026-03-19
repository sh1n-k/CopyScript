from __future__ import annotations

import importlib
import platform
from typing import Callable

from copyscript.config.languages import SUPPORTED_LANGUAGES

if platform.system() != "Darwin":
    raise ImportError("menubar module is macOS-only")

objc = importlib.import_module("objc")
appkit = importlib.import_module("AppKit")
foundation = importlib.import_module("Foundation")
NSMenu = appkit.NSMenu
NSMenuItem = appkit.NSMenuItem
NSStatusBar = appkit.NSStatusBar
NSVariableStatusItemLength = appkit.NSVariableStatusItemLength
NSObject = foundation.NSObject


class MenuBarDelegate(NSObject):
    def initWithCallbacks_(self, callbacks: dict[str, Callable]):
        self = objc.super(MenuBarDelegate, self).init()
        if self is None:
            return None
        self._callbacks = callbacks
        return self

    @objc.typedSelector(b"v@:@")
    def toggleMonitor_(self, sender):
        callback = self._callbacks.get("on_toggle")
        if callback:
            callback()

    @objc.typedSelector(b"v@:@")
    def selectLanguage_(self, sender):
        callback = self._callbacks.get("on_language")
        if callback:
            callback(str(sender.representedObject()))

    @objc.typedSelector(b"v@:@")
    def toggleTimestamp_(self, sender):
        callback = self._callbacks.get("on_timestamp")
        if callback:
            callback()

    @objc.typedSelector(b"v@:@")
    def showSettings_(self, sender):
        callback = self._callbacks.get("on_show_settings")
        if callback:
            callback()

    @objc.typedSelector(b"v@:@")
    def quitApp_(self, sender):
        callback = self._callbacks.get("on_quit")
        if callback:
            callback()


class MenuBarController:
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
        callbacks = {
            "on_toggle": on_toggle,
            "on_language": on_language,
            "on_timestamp": on_timestamp,
            "on_show_settings": on_show_settings,
            "on_quit": on_quit,
        }
        self._delegate = MenuBarDelegate.alloc().initWithCallbacks_(callbacks)
        status_bar = NSStatusBar.systemStatusBar()
        self._status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        self._status_item.setTitle_("CC")
        self._status_item.setHighlightMode_(True)
        self._menu = NSMenu.alloc().init()
        self._menu.setAutoenablesItems_(False)
        self._lang_items: dict[str, NSMenuItem] = {}
        self._build_menu(initial_lang, initial_timestamp, initial_running)
        self._status_item.setMenu_(self._menu)

    def _build_menu(self, lang_code: str, include_timestamp: bool, is_running: bool) -> None:
        self._menu.removeAllItems()
        status_text = "상태: 모니터링 중" if is_running else "상태: 정지됨"
        self._status_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            status_text,
            None,
            "",
        )
        self._status_menu_item.setEnabled_(False)
        self._menu.addItem_(self._status_menu_item)
        self._menu.addItem_(NSMenuItem.separatorItem())

        toggle_text = "\u23f9 정지" if is_running else "\u25b6 시작"
        self._toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            toggle_text,
            "toggleMonitor:",
            "",
        )
        self._toggle_item.setTarget_(self._delegate)
        self._menu.addItem_(self._toggle_item)
        self._menu.addItem_(NSMenuItem.separatorItem())

        lang_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("언어", None, "")
        lang_submenu = NSMenu.alloc().init()
        lang_submenu.setAutoenablesItems_(False)
        self._lang_items = {}
        for name, code in SUPPORTED_LANGUAGES:
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"{name} ({code})",
                "selectLanguage:",
                "",
            )
            item.setTarget_(self._delegate)
            item.setRepresentedObject_(code)
            item.setState_(1 if code == lang_code else 0)
            lang_submenu.addItem_(item)
            self._lang_items[code] = item
        lang_menu_item.setSubmenu_(lang_submenu)
        self._menu.addItem_(lang_menu_item)

        self._timestamp_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "타임스탬프 포함",
            "toggleTimestamp:",
            "",
        )
        self._timestamp_item.setTarget_(self._delegate)
        self._timestamp_item.setState_(1 if include_timestamp else 0)
        self._menu.addItem_(self._timestamp_item)
        self._menu.addItem_(NSMenuItem.separatorItem())

        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "설정 열기",
            "showSettings:",
            "",
        )
        settings_item.setTarget_(self._delegate)
        self._menu.addItem_(settings_item)
        self._menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("종료", "quitApp:", "")
        quit_item.setTarget_(self._delegate)
        self._menu.addItem_(quit_item)

    def update_running(self, is_running: bool) -> None:
        status_text = "상태: 모니터링 중" if is_running else "상태: 정지됨"
        self._status_menu_item.setTitle_(status_text)
        toggle_text = "\u23f9 정지" if is_running else "\u25b6 시작"
        self._toggle_item.setTitle_(toggle_text)

    def update_language(self, lang_code: str) -> None:
        for code, item in self._lang_items.items():
            item.setState_(1 if code == lang_code else 0)

    def update_timestamp(self, include: bool) -> None:
        self._timestamp_item.setState_(1 if include else 0)

    def cleanup(self) -> None:
        NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
