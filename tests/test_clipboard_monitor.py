import unittest
from unittest.mock import patch
import sys
import types

# 테스트 환경에서 외부 의존성 없는 import를 위해 스텁 주입
if "pyperclip" not in sys.modules:
    fake_pyperclip = types.ModuleType("pyperclip")
    fake_pyperclip.paste = lambda: ""
    fake_pyperclip.copy = lambda _text: None
    sys.modules["pyperclip"] = fake_pyperclip

if "subtitle_fetcher" not in sys.modules:
    fake_fetcher_module = types.ModuleType("subtitle_fetcher")

    class _DummySubtitleFetcher:
        preferred_lang = "ko"
        include_timestamp = False

    fake_fetcher_module.SubtitleFetcher = _DummySubtitleFetcher
    sys.modules["subtitle_fetcher"] = fake_fetcher_module

from clipboard_monitor import ClipboardMonitor


class DummyFetcher:
    def __init__(self):
        self.preferred_lang = "ko"
        self.include_timestamp = False
        self.fetch_calls = 0

    def fetch(self, video_id):
        self.fetch_calls += 1
        return "fetched line", None


class DummyCache:
    def __init__(self, text=None):
        self.text = text
        self.put_calls = []

    def get(self, video_id, lang_code, include_timestamp):
        return self.text

    def put(self, video_id, lang_code, include_timestamp, text):
        self.put_calls.append((video_id, lang_code, include_timestamp, text))


class ClipboardMonitorTest(unittest.TestCase):
    @patch("clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("clipboard_monitor.pyperclip.copy")
    @patch("clipboard_monitor.pyperclip.paste", return_value="https://youtu.be/abc123")
    def test_recopy_from_cache_when_already_processed(self, _paste, copy_mock, _extract):
        fetcher = DummyFetcher()
        cache = DummyCache(text="cached subtitle")
        results = []
        monitor = ClipboardMonitor(
            fetcher,
            on_processed=lambda vid, ok, detail: results.append((vid, ok, detail)),
            subtitle_cache=cache,
        )

        monitor._mark_processed("abc123")
        processed = monitor.check_and_process()

        self.assertTrue(processed)
        self.assertEqual(fetcher.fetch_calls, 0)
        copy_mock.assert_called_once_with("cached subtitle")
        self.assertTrue(results)
        self.assertTrue(results[0][1])
        self.assertIn("캐시 재복사", results[0][2])

    @patch("clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("clipboard_monitor.pyperclip.copy")
    @patch("clipboard_monitor.pyperclip.paste", return_value="https://youtu.be/abc123")
    def test_retry_fetch_when_cache_missing_for_processed_id(self, _paste, copy_mock, _extract):
        fetcher = DummyFetcher()
        cache = DummyCache(text=None)
        monitor = ClipboardMonitor(fetcher, subtitle_cache=cache)

        monitor._mark_processed("abc123")
        processed = monitor.check_and_process()

        self.assertTrue(processed)
        self.assertEqual(fetcher.fetch_calls, 1)
        copy_mock.assert_called_once_with("fetched line")
        self.assertEqual(len(cache.put_calls), 1)
        self.assertEqual(cache.put_calls[0][0], "abc123")


if __name__ == "__main__":
    unittest.main()
