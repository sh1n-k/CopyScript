from __future__ import annotations

import platform
import queue
import threading
import time
from typing import Any
from typing import Callable


class ClipboardWatcher:
    def __init__(self, on_change: Callable[[], None]):
        self._on_change = on_change

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class WindowsClipboardWatcher(ClipboardWatcher):
    def __init__(self, on_change: Callable[[], None]):
        super().__init__(on_change)
        self._msg_thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._hwnd = None
        self._wndproc = None
        self._class_name = "YTSubtitleClipboardListener"
        self._queue: queue.Queue[int] = queue.Queue()
        self._last_signal_ts = 0.0

    def start(self) -> None:
        if self._msg_thread and self._msg_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self._msg_thread = threading.Thread(target=self._run_message_loop, daemon=True)
        self._msg_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        try:
            import ctypes

            windll = getattr(ctypes, "windll", None)
            user32 = getattr(windll, "user32", None)
            if self._hwnd and user32 is not None:
                post_message = getattr(user32, "PostMessageW")
                post_message(self._hwnd, 0x0012, 0, 0)
        except Exception:
            pass
        if self._msg_thread:
            self._msg_thread.join(timeout=1.0)
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            now = time.monotonic()
            if now - self._last_signal_ts < 0.05:
                continue
            self._last_signal_ts = now
            try:
                self._on_change()
            except Exception:
                pass

    def _run_message_loop(self) -> None:
        import ctypes
        from ctypes import wintypes

        windll = getattr(ctypes, "windll")
        user32 = getattr(windll, "user32")
        kernel32 = getattr(windll, "kernel32")
        wm_clipboard_update = 0x031D
        wm_destroy = 0x0002
        hwnd_message = wintypes.HWND(-3)

        lresult_type: Any = getattr(wintypes, "LRESULT", ctypes.c_long)
        wndproc_type = getattr(ctypes, "WINFUNCTYPE")(
            lresult_type,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        def _wnd_proc(hwnd, msg, wparam, lparam):
            if msg == wm_clipboard_update:
                try:
                    self._queue.put_nowait(1)
                except Exception:
                    pass
                return 0
            if msg == wm_destroy:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = wndproc_type(_wnd_proc)

        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", wndproc_type),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HCURSOR),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        hinst = kernel32.GetModuleHandleW(None)
        wndclass = WNDCLASS()
        wndclass.style = 0
        wndclass.lpfnWndProc = self._wndproc
        wndclass.cbClsExtra = 0
        wndclass.cbWndExtra = 0
        wndclass.hInstance = hinst
        wndclass.hIcon = None
        wndclass.hCursor = None
        wndclass.hbrBackground = None
        wndclass.lpszMenuName = None
        wndclass.lpszClassName = self._class_name
        user32.RegisterClassW(ctypes.byref(wndclass))
        self._hwnd = user32.CreateWindowExW(
            0,
            self._class_name,
            self._class_name,
            0,
            0,
            0,
            0,
            0,
            hwnd_message,
            None,
            hinst,
            None,
        )
        if not self._hwnd:
            return
        if not user32.AddClipboardFormatListener(self._hwnd):
            return
        msg = wintypes.MSG()
        while not self._stop_event.is_set():
            ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if ret in (0, -1):
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        try:
            user32.RemoveClipboardFormatListener(self._hwnd)
        except Exception:
            pass
        try:
            user32.DestroyWindow(self._hwnd)
        except Exception:
            pass
        self._hwnd = None


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
