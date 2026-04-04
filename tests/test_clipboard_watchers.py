import ctypes
import threading
import types
import unittest

from copyscript.platform.clipboard_watchers import _get_wintype_attr
from copyscript.platform.clipboard_watchers import WindowsClipboardWatcher


class ClipboardWatchersTest(unittest.TestCase):
    def test_get_wintype_attr_returns_fallback_for_missing_handle_types(self):
        fake_wintypes = types.SimpleNamespace(HANDLE=ctypes.c_void_p)

        result = _get_wintype_attr(fake_wintypes, "HCURSOR", fake_wintypes.HANDLE)

        self.assertIs(result, ctypes.c_void_p)

    def test_windows_watcher_triggers_callback_when_sequence_changes(self):
        triggered = threading.Event()
        watcher = WindowsClipboardWatcher(triggered.set, interval_sec=0.05)
        sequence_values = iter([10, 10, 11, 11, 11])

        def _next_sequence():
            try:
                return next(sequence_values)
            except StopIteration:
                return 11

        watcher._get_sequence_number = _next_sequence  # type: ignore[method-assign]
        try:
            watcher.start()
            self.assertTrue(triggered.wait(0.4))
        finally:
            watcher.stop()

    def test_windows_watcher_does_not_trigger_without_sequence_change(self):
        triggered = threading.Event()
        watcher = WindowsClipboardWatcher(triggered.set, interval_sec=0.05)
        watcher._get_sequence_number = lambda: 25  # type: ignore[method-assign]

        try:
            watcher.start()
            self.assertFalse(triggered.wait(0.2))
        finally:
            watcher.stop()
