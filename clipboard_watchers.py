"""Windows/macOS 클립보드 변경 감지기.

- Windows: AddClipboardFormatListener + WM_CLIPBOARDUPDATE (진짜 이벤트 기반)
- macOS: NSPasteboard.changeCount (가벼운 폴링, 변경 시에만 처리)
"""

from __future__ import annotations

import platform
import queue
import threading
import time
from typing import Callable, Optional


class ClipboardWatcher:
    """플랫폼별 클립보드 변경 감지기.

    on_change는 "클립보드가 바뀌었다"는 신호만 전달해야 합니다.
    (무거운 작업은 on_change 내부에서 하더라도 watcher 이벤트 루프를 막지 않도록 설계)
    """

    def __init__(self, on_change: Callable[[], None]):
        self._on_change = on_change

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


# ------------------------
# Windows: WM_CLIPBOARDUPDATE 이벤트 기반
# ------------------------
class WindowsClipboardWatcher(ClipboardWatcher):
    def __init__(self, on_change: Callable[[], None]):
        super().__init__(on_change)

        self._msg_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None

        self._stop_event = threading.Event()
        self._hwnd = None
        self._wndproc = None
        self._class_name = "YTSubtitleClipboardListener"

        # 윈도우 메시지 핸들러(윈도우 스레드)에서 무거운 작업을 하면 안 됨 → 큐로 넘김
        self._q: "queue.Queue[int]" = queue.Queue()
        self._last_signal_ts = 0.0  # 간단 디바운스

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

        # 메시지 루프 깨우기
        try:
            import ctypes

            user32 = ctypes.windll.user32
            if self._hwnd:
                user32.PostMessageW(self._hwnd, 0x0012, 0, 0)  # WM_QUIT
        except Exception:
            pass

        if self._msg_thread:
            self._msg_thread.join(timeout=1.0)
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._q.get(timeout=0.2)
            except queue.Empty:
                continue

            # 아주 짧은 디바운스(연속 이벤트 폭주 방지)
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

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        WM_CLIPBOARDUPDATE = 0x031D
        WM_DESTROY = 0x0002
        HWND_MESSAGE = wintypes.HWND(-3)

        WNDPROCTYPE = ctypes.WINFUNCTYPE(
            wintypes.LRESULT,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        def _wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_CLIPBOARDUPDATE:
                # 여기서 무거운 작업 금지 → 큐에 신호만
                try:
                    self._q.put_nowait(1)
                except Exception:
                    pass
                return 0

            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0

            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = WNDPROCTYPE(_wnd_proc)

        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROCTYPE),
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

        # RegisterClassW는 실패해도(이미 등록됨 등) CreateWindow가 성공할 수 있음
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
            HWND_MESSAGE,
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
            if ret == 0:  # WM_QUIT
                break
            if ret == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # cleanup
        try:
            user32.RemoveClipboardFormatListener(self._hwnd)
        except Exception:
            pass
        try:
            user32.DestroyWindow(self._hwnd)
        except Exception:
            pass

        self._hwnd = None


# ------------------------
# macOS: NSPasteboard.changeCount 기반(가벼운 폴링)
# ------------------------
class MacClipboardWatcher(ClipboardWatcher):
    def __init__(self, on_change: Callable[[], None], interval_sec: float = 0.25):
        super().__init__(on_change)
        self._interval = max(0.05, float(interval_sec))
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._last_signal_ts = 0.0  # 간단 디바운스

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
            # pyobjc 미설치 시 동작 불가
            return

        pb = NSPasteboard.generalPasteboard()
        last = pb.changeCount()

        while not self._stop_event.is_set():
            time.sleep(self._interval)
            cur = pb.changeCount()
            if cur == last:
                continue
            last = cur

            # 디바운스
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