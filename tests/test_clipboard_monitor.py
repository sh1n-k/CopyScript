import unittest
from unittest.mock import patch
import sys
import types

from copyscript.config.models import ProcessingOptions

# 테스트 환경에서 외부 의존성 없는 import를 위해 스텁 주입
if "pyperclip" not in sys.modules:
    fake_pyperclip = types.ModuleType("pyperclip")
    setattr(fake_pyperclip, "paste", lambda: "")
    setattr(fake_pyperclip, "copy", lambda _text: None)
    sys.modules["pyperclip"] = fake_pyperclip

from copyscript.core.clipboard_monitor import (  # noqa: E402
    ClipboardMonitor,
    _normalize_clipboard_text,
)


class DummyFetcher:
    def __init__(self):
        self.preferred_lang = "ko"
        self.include_timestamp = False
        self.fetch_calls = 0
        self.options_seen = []

    def get_options(self):
        return ProcessingOptions(self.preferred_lang, self.include_timestamp)

    def fetch(self, video_id, options=None):
        self.fetch_calls += 1
        self.options_seen.append(options)
        return "fetched line", None


class DummyCache:
    def __init__(self, text=None):
        self.text = text
        self.put_calls = []

    def get(self, video_id, lang_code, include_timestamp):
        return self.text

    def put(self, video_id, lang_code, include_timestamp, text):
        self.put_calls.append((video_id, lang_code, include_timestamp, text))
        self.text = text


class ClipboardMonitorTest(unittest.TestCase):
    def setUp(self):
        self.settle_patcher = patch(
            "copyscript.core.clipboard_monitor._POST_COPY_SETTLE_SEC", 0
        )
        self.delay_patcher = patch(
            "copyscript.core.clipboard_monitor._WRITE_RETRY_DELAYS_SEC", (0, 0)
        )
        self.settle_patcher.start()
        self.delay_patcher.start()

    def tearDown(self):
        self.settle_patcher.stop()
        self.delay_patcher.stop()

    def _paste_side_effect(self, *values):
        queue = list(values)

        def _paste():
            if not queue:
                return values[-1] if values else ""
            return queue.pop(0)

        return _paste

    @patch("copyscript.core.clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("copyscript.core.clipboard_monitor.pyperclip.copy")
    @patch("copyscript.core.clipboard_monitor.pyperclip.paste")
    def test_recopy_from_cache_when_already_processed(
        self, paste_mock, copy_mock, _extract
    ):
        paste_mock.side_effect = self._paste_side_effect(
            "https://youtu.be/abc123",
            "cached subtitle",
        )
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

    @patch("copyscript.core.clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("copyscript.core.clipboard_monitor.pyperclip.copy")
    @patch("copyscript.core.clipboard_monitor.pyperclip.paste")
    def test_retry_fetch_when_cache_missing_for_processed_id(
        self, paste_mock, copy_mock, _extract
    ):
        paste_mock.side_effect = self._paste_side_effect(
            "https://youtu.be/abc123",
            "fetched line",
        )
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

    @patch("copyscript.core.clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("copyscript.core.clipboard_monitor.pyperclip.copy")
    @patch("copyscript.core.clipboard_monitor.pyperclip.paste")
    def test_processing_uses_snapshot_options(self, paste_mock, copy_mock, _extract):
        paste_mock.side_effect = self._paste_side_effect(
            "https://youtu.be/abc123",
            "fetched line",
        )
        fetcher = DummyFetcher()
        cache = DummyCache(text=None)
        options = ProcessingOptions(lang_code="en", include_timestamp=True)
        monitor = ClipboardMonitor(
            fetcher,
            subtitle_cache=cache,
            options_provider=lambda: options,
        )

        processed = monitor.check_and_process()

        self.assertTrue(processed)
        self.assertEqual(fetcher.options_seen[-1], options)
        self.assertEqual(cache.put_calls[0][1], "en")
        self.assertTrue(cache.put_calls[0][2])

    @patch("copyscript.core.clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("copyscript.core.clipboard_monitor.pyperclip.copy")
    @patch("copyscript.core.clipboard_monitor.pyperclip.paste")
    def test_verify_success_after_normalized_newline_mismatch(
        self, paste_mock, copy_mock, _extract
    ):
        paste_mock.side_effect = self._paste_side_effect(
            "https://youtu.be/abc123",
            "fetched line\r\n",
        )
        fetcher = DummyFetcher()
        fetcher.fetch = lambda video_id, options=None: ("fetched line\n", None)
        monitor = ClipboardMonitor(fetcher, subtitle_cache=DummyCache())

        self.assertTrue(monitor.check_and_process())
        self.assertEqual(monitor._last_clipboard, "fetched line\n")
        self.assertIn("abc123", monitor._processed_ids)

    @patch("copyscript.core.clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("copyscript.core.clipboard_monitor.pyperclip.copy")
    @patch("copyscript.core.clipboard_monitor.pyperclip.paste")
    def test_verify_retries_then_succeeds(self, paste_mock, copy_mock, _extract):
        paste_mock.side_effect = self._paste_side_effect(
            "https://youtu.be/abc123",
            "https://youtu.be/abc123",  # mismatch attempt 1
            "fetched line",  # ok attempt 2
        )
        fetcher = DummyFetcher()
        results = []
        monitor = ClipboardMonitor(
            fetcher,
            on_processed=lambda vid, ok, detail: results.append((vid, ok, detail)),
            subtitle_cache=DummyCache(),
        )

        self.assertTrue(monitor.check_and_process())
        self.assertEqual(copy_mock.call_count, 2)
        self.assertTrue(results[-1][1])

    @patch("copyscript.core.clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("copyscript.core.clipboard_monitor.pyperclip.copy")
    @patch("copyscript.core.clipboard_monitor.pyperclip.paste")
    def test_verify_failure_keeps_cache_clears_last_and_skips_processed(
        self, paste_mock, copy_mock, _extract
    ):
        paste_mock.side_effect = self._paste_side_effect(
            "https://youtu.be/abc123",
            "https://youtu.be/abc123",
            "https://youtu.be/abc123",
            "https://youtu.be/abc123",
        )
        fetcher = DummyFetcher()
        cache = DummyCache(text=None)
        results = []
        rechecks = []
        monitor = ClipboardMonitor(
            fetcher,
            on_processed=lambda vid, ok, detail: results.append((vid, ok, detail)),
            subtitle_cache=cache,
            on_need_recheck=lambda: rechecks.append(1),
        )

        self.assertFalse(monitor.check_and_process())
        self.assertEqual(copy_mock.call_count, 3)
        self.assertEqual(len(cache.put_calls), 1)
        self.assertEqual(cache.text, "fetched line")
        self.assertNotIn("abc123", monitor._processed_ids)
        self.assertEqual(monitor._last_clipboard, "")
        self.assertFalse(results[-1][1])
        self.assertIn("반영되지 않음", results[-1][2])
        self.assertEqual(len(rechecks), 1)
        self.assertEqual(monitor._auto_recheck_video_id, "abc123")

    @patch("copyscript.core.clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("copyscript.core.clipboard_monitor.pyperclip.copy")
    @patch("copyscript.core.clipboard_monitor.pyperclip.paste")
    def test_verify_read_error_message(self, paste_mock, copy_mock, _extract):
        def paste_side_effect():
            if paste_side_effect.calls == 0:
                paste_side_effect.calls += 1
                return "https://youtu.be/abc123"
            raise RuntimeError("clipboard locked")

        paste_side_effect.calls = 0
        paste_mock.side_effect = paste_side_effect
        results = []
        monitor = ClipboardMonitor(
            DummyFetcher(),
            on_processed=lambda vid, ok, detail: results.append((vid, ok, detail)),
            subtitle_cache=DummyCache(),
        )

        self.assertFalse(monitor.check_and_process())
        self.assertFalse(results[-1][1])
        self.assertIn("확인 실패", results[-1][2])

    @patch("copyscript.core.clipboard_monitor.extract_video_id", return_value="abc123")
    @patch("copyscript.core.clipboard_monitor.pyperclip.copy")
    @patch("copyscript.core.clipboard_monitor.pyperclip.paste")
    def test_auto_recheck_uses_cache_and_is_one_shot(
        self, paste_mock, copy_mock, _extract
    ):
        paste_mock.side_effect = self._paste_side_effect(
            # first process: detect + 3 failed verifies
            "https://youtu.be/abc123",
            "stale",
            "stale",
            "stale",
            # auto recheck: detect + success
            "https://youtu.be/abc123",
            "fetched line",
        )
        fetcher = DummyFetcher()
        cache = DummyCache(text=None)
        rechecks = []
        results = []
        monitor = ClipboardMonitor(
            fetcher,
            on_processed=lambda vid, ok, detail: results.append((vid, ok, detail)),
            subtitle_cache=cache,
            on_need_recheck=lambda: rechecks.append(1),
        )

        self.assertFalse(monitor.check_and_process())
        self.assertEqual(fetcher.fetch_calls, 1)
        self.assertEqual(len(rechecks), 1)

        self.assertTrue(monitor.check_and_process())
        self.assertEqual(fetcher.fetch_calls, 1)
        self.assertTrue(results[-1][1])
        self.assertIn("캐시 재복사", results[-1][2])
        self.assertIsNone(monitor._auto_recheck_video_id)

        # Consecutive write failures for the same video must not loop rechecks.
        paste_mock.side_effect = self._paste_side_effect(
            "https://youtu.be/abc123",
            "bad",
            "bad",
            "bad",
            "https://youtu.be/abc123",
            "bad",
            "bad",
            "bad",
        )
        rechecks.clear()
        monitor._last_clipboard = ""
        monitor._processed_ids.clear()
        cache.text = "fetched line"
        # Simulate prior write-fail that already reserved one auto-recheck.
        monitor._auto_recheck_video_id = "abc123"
        self.assertFalse(monitor.check_and_process())
        self.assertEqual(len(rechecks), 0)
        self.assertIsNone(monitor._auto_recheck_video_id)

    def test_normalize_clipboard_text(self):
        self.assertEqual(_normalize_clipboard_text("a\r\nb\rc"), "a\nb\nc")


if __name__ == "__main__":
    unittest.main()
