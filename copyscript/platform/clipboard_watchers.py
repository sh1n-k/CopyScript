from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import logging
import platform
import queue
import threading
import time
from typing import Any
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


@dataclass
class _WindowsWatcherSession:
    session_id: int
    class_name: str
    stop_event: threading.Event = field(default_factory=threading.Event)
    queue: queue.Queue[int] = field(default_factory=queue.Queue)
    hwnd: Any = None
    wndproc: Any = None
    worker_thread: threading.Thread | None = None
    msg_thread: threading.Thread | None = None
    last_signal_ts: float = 0.0


class WindowsClipboardWatcher(ClipboardWatcher):
    def __init__(self, on_change: Callable[[], None]):
        super().__init__(on_change)
        self._session_lock = threading.Lock()
        self._session: _WindowsWatcherSession | None = None
        self._next_session_id = 0

    def _create_session(self) -> _WindowsWatcherSession:
        self._next_session_id += 1
        session_id = self._next_session_id
        return _WindowsWatcherSession(
            session_id=session_id,
            class_name=f"YTSubtitleClipboardListener{session_id}",
        )

    def start(self) -> None:
        with self._session_lock:
            if self._session and self._session.msg_thread and self._session.msg_thread.is_alive():
                logger.debug("Watcher start ignored; session %s is already active", self._session.session_id)
                return
            session = self._create_session()
            session.worker_thread = threading.Thread(
                target=self._worker_loop,
                args=(session,),
                name=f"clipboard-worker-{session.session_id}",
                daemon=True,
            )
            session.msg_thread = threading.Thread(
                target=self._run_message_loop,
                args=(session,),
                name=f"clipboard-msg-{session.session_id}",
                daemon=True,
            )
            self._session = session
        logger.info("Starting Windows clipboard watcher session %s", session.session_id)
        session.worker_thread.start()
        session.msg_thread.start()

    def stop(self) -> None:
        with self._session_lock:
            session = self._session
            self._session = None
        if session is None:
            logger.debug("Watcher stop ignored; no active session")
            return
        logger.info("Stopping Windows clipboard watcher session %s", session.session_id)
        session.stop_event.set()
        self._post_close_message(session)
        if session.msg_thread:
            session.msg_thread.join(timeout=2.0)
            logger.debug(
                "Session %s message thread alive after join: %s",
                session.session_id,
                session.msg_thread.is_alive(),
            )
        if session.worker_thread:
            session.worker_thread.join(timeout=2.0)
            logger.debug(
                "Session %s worker thread alive after join: %s",
                session.session_id,
                session.worker_thread.is_alive(),
            )

    def _post_close_message(self, session: _WindowsWatcherSession) -> None:
        try:
            import ctypes

            windll = getattr(ctypes, "windll", None)
            user32 = getattr(windll, "user32", None)
            if session.hwnd and user32 is not None:
                post_message = getattr(user32, "PostMessageW")
                logger.debug(
                    "Posting WM_CLOSE to watcher session %s hwnd=%s",
                    session.session_id,
                    session.hwnd,
                )
                post_message(session.hwnd, 0x0012, 0, 0)
        except Exception:
            logger.exception("Failed to post WM_CLOSE to watcher session %s", session.session_id)

    def _worker_loop(self, session: _WindowsWatcherSession) -> None:
        logger.debug("Worker loop started for session %s", session.session_id)
        while not session.stop_event.is_set():
            try:
                session.queue.get(timeout=0.2)
            except queue.Empty:
                continue
            now = time.monotonic()
            if now - session.last_signal_ts < 0.05:
                continue
            session.last_signal_ts = now
            try:
                logger.debug("Dispatching clipboard change from session %s", session.session_id)
                self._on_change()
            except Exception:
                logger.exception("Unhandled error in clipboard change callback for session %s", session.session_id)
        logger.debug("Worker loop exited for session %s", session.session_id)

    def _run_message_loop(self, session: _WindowsWatcherSession) -> None:
        import ctypes
        from ctypes import wintypes

        windll = getattr(ctypes, "windll")
        user32 = getattr(windll, "user32")
        kernel32 = getattr(windll, "kernel32")
        wm_clipboard_update = 0x031D
        wm_destroy = 0x0002
        hwnd_message = wintypes.HWND(-3)

        lresult_type: Any = getattr(wintypes, "LRESULT", ctypes.c_long)
        hcursor_type = _get_wintype_attr(wintypes, "HCURSOR", wintypes.HANDLE)
        hicon_type = _get_wintype_attr(wintypes, "HICON", wintypes.HANDLE)
        hbrush_type = _get_wintype_attr(wintypes, "HBRUSH", wintypes.HANDLE)
        wndproc_type = getattr(ctypes, "WINFUNCTYPE")(
            lresult_type,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        user32.DefWindowProcW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.DefWindowProcW.restype = lresult_type

        def _wnd_proc(hwnd, msg, wparam, lparam):
            if msg == wm_clipboard_update:
                try:
                    session.queue.put_nowait(1)
                except Exception:
                    logger.exception("Failed to enqueue clipboard update for session %s", session.session_id)
                return 0
            if msg == wm_destroy:
                logger.debug("WM_DESTROY received for watcher session %s hwnd=%s", session.session_id, hwnd)
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        session.wndproc = wndproc_type(_wnd_proc)

        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", wndproc_type),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", hicon_type),
                ("hCursor", hcursor_type),
                ("hbrBackground", hbrush_type),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        hinst = kernel32.GetModuleHandleW(None)
        wndclass = WNDCLASS()
        wndclass.style = 0
        wndclass.lpfnWndProc = session.wndproc
        wndclass.cbClsExtra = 0
        wndclass.cbWndExtra = 0
        wndclass.hInstance = hinst
        wndclass.hIcon = None
        wndclass.hCursor = None
        wndclass.hbrBackground = None
        wndclass.lpszMenuName = None
        wndclass.lpszClassName = session.class_name
        atom = user32.RegisterClassW(ctypes.byref(wndclass))
        if not atom:
            logger.error(
                "RegisterClassW failed for session %s class=%s error=%s",
                session.session_id,
                session.class_name,
                ctypes.GetLastError(),
            )
            return
        logger.debug(
            "Registered watcher window class for session %s class=%s",
            session.session_id,
            session.class_name,
        )
        session.hwnd = user32.CreateWindowExW(
            0,
            session.class_name,
            session.class_name,
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
        if not session.hwnd:
            logger.error(
                "CreateWindowExW failed for session %s error=%s",
                session.session_id,
                ctypes.GetLastError(),
            )
            user32.UnregisterClassW(session.class_name, hinst)
            return
        logger.info(
            "Created watcher message window for session %s hwnd=%s",
            session.session_id,
            session.hwnd,
        )
        if not user32.AddClipboardFormatListener(session.hwnd):
            logger.error(
                "AddClipboardFormatListener failed for session %s hwnd=%s error=%s",
                session.session_id,
                session.hwnd,
                ctypes.GetLastError(),
            )
            user32.DestroyWindow(session.hwnd)
            user32.UnregisterClassW(session.class_name, hinst)
            session.hwnd = None
            return
        logger.info("Clipboard listener active for session %s", session.session_id)
        msg = wintypes.MSG()
        try:
            while not session.stop_event.is_set():
                ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                if ret == -1:
                    logger.error(
                        "GetMessageW returned -1 for session %s error=%s",
                        session.session_id,
                        ctypes.GetLastError(),
                    )
                    break
                if ret == 0:
                    logger.debug("Message loop received WM_QUIT for session %s", session.session_id)
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            try:
                user32.RemoveClipboardFormatListener(session.hwnd)
                logger.debug("Removed clipboard listener for session %s", session.session_id)
            except Exception:
                logger.exception("Failed to remove clipboard listener for session %s", session.session_id)
            try:
                user32.DestroyWindow(session.hwnd)
                logger.debug("Destroyed watcher window for session %s", session.session_id)
            except Exception:
                logger.exception("Failed to destroy watcher window for session %s", session.session_id)
            try:
                user32.UnregisterClassW(session.class_name, hinst)
                logger.debug(
                    "Unregistered watcher window class for session %s class=%s",
                    session.session_id,
                    session.class_name,
                )
            except Exception:
                logger.exception(
                    "Failed to unregister watcher window class for session %s",
                    session.session_id,
                )
            session.hwnd = None
            session.wndproc = None
            logger.debug("Message loop exited for session %s", session.session_id)


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
