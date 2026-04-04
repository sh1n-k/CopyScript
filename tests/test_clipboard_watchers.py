import ctypes
import types
import unittest

from copyscript.platform.clipboard_watchers import _get_wintype_attr
from copyscript.platform.clipboard_watchers import WindowsClipboardWatcher


class ClipboardWatchersTest(unittest.TestCase):
    def test_get_wintype_attr_returns_fallback_for_missing_handle_types(self):
        fake_wintypes = types.SimpleNamespace(HANDLE=ctypes.c_void_p)

        result = _get_wintype_attr(fake_wintypes, "HCURSOR", fake_wintypes.HANDLE)

        self.assertIs(result, ctypes.c_void_p)

    def test_windows_watcher_creates_unique_session_class_names(self):
        watcher = WindowsClipboardWatcher(lambda: None)

        session1 = watcher._create_session()
        session2 = watcher._create_session()

        self.assertNotEqual(session1.session_id, session2.session_id)
        self.assertNotEqual(session1.class_name, session2.class_name)
