from __future__ import annotations

import logging
import platform
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)


class ClipboardWatcher:
    def __init__(self, on_change: Callable[[], None]):
        self._on_change = on_change

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


def _get_wintype_attr(wintypes_module, name: str, fallback):
    return getattr(wintypes_module, name, fallback)


class WindowsClipboardWatcher(ClipboardWatcher):
    def __init__(self, on_change: Callable[[], None], interval_sec: float = 0.25):
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
    def __init__(self, on_change: Callable[[], None], interval_sec: float = 0.25):
        super().__init__(on_change)
        self._interval = max(0.05, float(interval_sec))
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_signal_ts = 0.0

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

    def _run(self) -> None:
        try:
            from AppKit import NSPasteboard  # type: ignore
        except Exception:
            return
        pasteboard = NSPasteboard.generalPasteboard()
        last = pasteboard.changeCount()
        while not self._stop_event.is_set():
            time.sleep(self._interval)
            current = pasteboard.changeCount()
            if current == last:
                continue
            last = current
            now = time.monotonic()
            if now - self._last_signal_ts < 0.05:
                continue
            self._last_signal_ts = now
            try:
                self._on_change()
            except Exception:
                pass


def create_watcher(on_change: Callable[[], None]) -> ClipboardWatcher:
    system = platform.system()
    if system == "Windows":
        return WindowsClipboardWatcher(on_change)
    if system == "Darwin":
        return MacClipboardWatcher(on_change)
    raise RuntimeError("This app supports Windows/macOS only.")
