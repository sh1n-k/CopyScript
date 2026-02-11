"""macOS 메뉴바 컨트롤러 - NSStatusItem + NSMenu"""

from __future__ import annotations

import platform
from typing import Callable

if platform.system() != "Darwin":
    raise ImportError("menubar module is macOS-only")

import objc
from AppKit import (
    NSApplication,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject

from subtitle_fetcher import SUPPORTED_LANGUAGES


class MenuBarDelegate(NSObject):
    """Objective-C 호환 델리게이트: target-action 셀렉터 → Python 콜백"""

    def initWithCallbacks_(self, callbacks: dict[str, Callable]):
        self = objc.super(MenuBarDelegate, self).init()
        if self is None:
            return None
        self._callbacks = callbacks
        return self

    @objc.typedSelector(b"v@:@")
    def toggleMonitor_(self, sender):
        cb = self._callbacks.get("on_toggle")
        if cb:
            cb()

    @objc.typedSelector(b"v@:@")
    def selectLanguage_(self, sender):
        cb = self._callbacks.get("on_language")
        if cb:
            tag = sender.tag()
            if 0 <= tag < len(SUPPORTED_LANGUAGES):
                cb(SUPPORTED_LANGUAGES[tag][1])

    @objc.typedSelector(b"v@:@")
    def toggleTimestamp_(self, sender):
        cb = self._callbacks.get("on_timestamp")
        if cb:
            cb()

    @objc.typedSelector(b"v@:@")
    def showSettings_(self, sender):
        cb = self._callbacks.get("on_show_settings")
        if cb:
            cb()

    @objc.typedSelector(b"v@:@")
    def quitApp_(self, sender):
        cb = self._callbacks.get("on_quit")
        if cb:
            cb()


class MenuBarController:
    """NSStatusItem 생성, NSMenu 빌드, 상태 업데이트 API"""

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
        self._build_menu(initial_lang, initial_timestamp, initial_running)
        self._status_item.setMenu_(self._menu)

    def _build_menu(self, lang_code: str, include_timestamp: bool, is_running: bool):
        self._menu.removeAllItems()

        # 상태 표시
        status_text = "상태: 모니터링 중" if is_running else "상태: 정지됨"
        self._status_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            status_text, None, ""
        )
        self._status_menu_item.setEnabled_(False)
        self._menu.addItem_(self._status_menu_item)

        self._menu.addItem_(NSMenuItem.separatorItem())

        # 시작/정지 토글
        toggle_text = "\u23f9 정지" if is_running else "\u25b6 시작"
        self._toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            toggle_text, "toggleMonitor:", ""
        )
        self._toggle_item.setTarget_(self._delegate)
        self._menu.addItem_(self._toggle_item)

        self._menu.addItem_(NSMenuItem.separatorItem())

        # 언어 서브메뉴
        lang_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "언어", None, ""
        )
        lang_submenu = NSMenu.alloc().init()
        lang_submenu.setAutoenablesItems_(False)
        self._lang_items: list[NSMenuItem] = []
        for idx, (name, code) in enumerate(SUPPORTED_LANGUAGES):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"{name} ({code})", "selectLanguage:", ""
            )
            item.setTarget_(self._delegate)
            item.setTag_(idx)
            if code == lang_code:
                item.setState_(1)  # NSOnState
            lang_submenu.addItem_(item)
            self._lang_items.append(item)
        lang_menu_item.setSubmenu_(lang_submenu)
        self._menu.addItem_(lang_menu_item)

        # 타임스탬프 토글
        self._timestamp_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "타임스탬프 포함", "toggleTimestamp:", ""
        )
        self._timestamp_item.setTarget_(self._delegate)
        self._timestamp_item.setState_(1 if include_timestamp else 0)
        self._menu.addItem_(self._timestamp_item)

        self._menu.addItem_(NSMenuItem.separatorItem())

        # 설정 열기
        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "설정 열기", "showSettings:", ""
        )
        settings_item.setTarget_(self._delegate)
        self._menu.addItem_(settings_item)

        self._menu.addItem_(NSMenuItem.separatorItem())

        # 종료
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "종료", "quitApp:", ""
        )
        quit_item.setTarget_(self._delegate)
        self._menu.addItem_(quit_item)

    def update_running(self, is_running: bool) -> None:
        status_text = "상태: 모니터링 중" if is_running else "상태: 정지됨"
        self._status_menu_item.setTitle_(status_text)
        toggle_text = "\u23f9 정지" if is_running else "\u25b6 시작"
        self._toggle_item.setTitle_(toggle_text)

    def update_language(self, lang_code: str) -> None:
        for idx, (_, code) in enumerate(SUPPORTED_LANGUAGES):
            self._lang_items[idx].setState_(1 if code == lang_code else 0)

    def update_timestamp(self, include: bool) -> None:
        self._timestamp_item.setState_(1 if include else 0)

    def cleanup(self) -> None:
        NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
