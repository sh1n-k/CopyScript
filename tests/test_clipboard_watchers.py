import ctypes
import types
import unittest

from copyscript.platform.clipboard_watchers import _get_wintype_attr


class ClipboardWatchersTest(unittest.TestCase):
    def test_get_wintype_attr_returns_fallback_for_missing_handle_types(self):
        fake_wintypes = types.SimpleNamespace(HANDLE=ctypes.c_void_p)

        result = _get_wintype_attr(fake_wintypes, "HCURSOR", fake_wintypes.HANDLE)

        self.assertIs(result, ctypes.c_void_p)
