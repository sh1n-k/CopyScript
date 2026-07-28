from __future__ import annotations

from collections.abc import Callable
import logging
import platform
import threading
import time

import pyperclip

logger = logging.getLogger(__name__)


class ClipboardWatcher:
    def __init__(self, on_change: Callable[[], None]) -> None:
        self._on_change = on_change

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def invalidate_baseline(self) -> None:
        """Force the next poll to treat the current clipboard as changed."""
        return


def _get_wintype_attr(wintypes_module: object, name: str, fallback: object) -> object:
    return getattr(wintypes_module, name, fallback)


class WindowsClipboardWatcher(ClipboardWatcher):
    def __init__(
        self, on_change: Callable[[], None], interval_sec: float = 0.25
    ) -> None:
        super().__init__(on_change)
        self._interval = max(0.05, float(interval_sec))
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_signal_ts = 0.0
        self._last_sequence_number: int | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.debug("Watcher start ignored; polling thread is already active")
            return
        self._stop_event.clear()
        self._last_sequence_number = self._get_sequence_number()
        logger.info(
            "Starting Windows clipboard watcher polling (interval=%ss, baseline=%s)",
            self._interval,
            self._last_sequence_number,
        )
        self._thread = threading.Thread(
            target=self._run,
            name="clipboard-polling",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if not self._thread:
            logger.debug("Watcher stop ignored; no active polling thread")
            return
        logger.info("Stopping Windows clipboard watcher polling")
        self._stop_event.set()
        self._thread.join(timeout=2.0)
        logger.debug("Polling thread alive after join: %s", self._thread.is_alive())
        self._thread = None

    def invalidate_baseline(self) -> None:
        self._last_sequence_number = None

    def _get_sequence_number(self) -> int | None:
        try:
            import ctypes

            windll = getattr(ctypes, "windll", None)
            user32 = getattr(windll, "user32", None)
            if user32 is None:
                return None
            get_sequence_number = getattr(user32, "GetClipboardSequenceNumber", None)
            if get_sequence_number is None:
                return None
            return int(get_sequence_number())
        except Exception:
            logger.exception("Failed to read clipboard sequence number")
            return None

    def _run(self) -> None:
        logger.debug("Windows clipboard polling loop started")
        while not self._stop_event.is_set():
            time.sleep(self._interval)
            current = self._get_sequence_number()
            if current is None or current == self._last_sequence_number:
                continue
            self._last_sequence_number = current
            now = time.monotonic()
            if now - self._last_signal_ts < 0.05:
                continue
            self._last_signal_ts = now
            try:
                logger.debug("Clipboard sequence changed to %s", current)
                self._on_change()
            except Exception:
                logger.exception("Unhandled error in clipboard change callback")
        logger.debug("Windows clipboard polling loop exited")


class MacClipboardWatcher(ClipboardWatcher):
    def __init__(
        self, on_change: Callable[[], None], interval_sec: float = 0.25
    ) -> None:
        super().__init__(on_change)
        self._interval = max(0.05, float(interval_sec))
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_signal_ts = 0.0
        self._last_change_count: int | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def invalidate_baseline(self) -> None:
        self._last_change_count = None

    def _run(self) -> None:
        try:
            from AppKit import NSPasteboard  # type: ignore
        except ImportError:
            logger.warning(
                "AppKit is not available; macOS clipboard watcher cannot start"
            )
            return
        pasteboard = NSPasteboard.generalPasteboard()
        self._last_change_count = pasteboard.changeCount()
        while not self._stop_event.is_set():
            time.sleep(self._interval)
            current = pasteboard.changeCount()
            if (
                self._last_change_count is not None
                and current == self._last_change_count
            ):
                continue
            self._last_change_count = current
            now = time.monotonic()
            if now - self._last_signal_ts < 0.05:
                continue
            self._last_signal_ts = now
            try:
                self._on_change()
            except Exception:
                logger.exception("Unhandled error in clipboard change callback")


class LinuxClipboardWatcher(ClipboardWatcher):
    def __init__(self, on_change: Callable[[], None], interval_sec: float = 0.5):
        super().__init__(on_change)
        self._interval = max(0.1, float(interval_sec))
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_signal_ts = 0.0
        self._last_value: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._last_value = self._read_clipboard()
        self._thread = threading.Thread(
            target=self._run,
            name="clipboard-polling",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def invalidate_baseline(self) -> None:
        self._last_value = None

    def _read_clipboard(self) -> str | None:
        try:
            value = pyperclip.paste()
        except Exception:
            return None
        return value if isinstance(value, str) else None

    def _run(self) -> None:
        logger.debug("Linux clipboard polling loop started")
        while not self._stop_event.is_set():
            time.sleep(self._interval)
            current = self._read_clipboard()
            if current is None or current == self._last_value:
                continue
            self._last_value = current
            now = time.monotonic()
            if now - self._last_signal_ts < 0.05:
                continue
            self._last_signal_ts = now
            try:
                self._on_change()
            except Exception:
                logger.exception("Unhandled error in clipboard change callback")
        logger.debug("Linux clipboard polling loop exited")


def create_watcher(on_change: Callable[[], None]) -> ClipboardWatcher:
    system = platform.system()
    if system == "Windows":
        return WindowsClipboardWatcher(on_change)
    if system == "Darwin":
        return MacClipboardWatcher(on_change)
    if system == "Linux":
        return LinuxClipboardWatcher(on_change)
    raise RuntimeError("This app supports Windows/macOS/Linux only.")
