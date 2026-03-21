import tempfile
import unittest
from pathlib import Path

from copyscript.app.settings_store import SettingsStore
from copyscript.config.models import AppSettings, HistoryEntry


class SettingsStoreTest(unittest.TestCase):
    def test_round_trip_preserves_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingsStore()
            store.settings_path = Path(tmp) / "settings.json"
            settings = AppSettings(
                lang_code="en",
                include_timestamp=True,
                monitor_on_launch=False,
                launch_at_login=True,
                cache_max_items=25,
                window_geometry="480x640+10+20",
                recent_history=[HistoryEntry("10:00:00", "성공", "abc123", "3줄 복사")],
            )

            store.save(settings)
            loaded = store.load()

            self.assertEqual(loaded.lang_code, "en")
            self.assertTrue(loaded.include_timestamp)
            self.assertFalse(loaded.monitor_on_launch)
            self.assertTrue(loaded.launch_at_login)
            self.assertEqual(loaded.cache_max_items, 25)
            self.assertEqual(loaded.window_geometry, "480x640+10+20")
            self.assertEqual(len(loaded.recent_history), 1)
            self.assertEqual(loaded.recent_history[0].detail, "3줄 복사")

    def test_legacy_auto_start_maps_to_monitor_on_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingsStore()
            store.settings_path = Path(tmp) / "settings.json"
            store.settings_path.write_text('{"auto_start": false}', encoding="utf-8")

            loaded = store.load()

            self.assertFalse(loaded.monitor_on_launch)
            self.assertTrue(loaded.launch_at_login)

    def test_invalid_history_is_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingsStore()
            store.settings_path = Path(tmp) / "settings.json"
            store.settings_path.write_text('{"recent_history": [1, {"time": "x", "status": "성공"}]}', encoding="utf-8")

            loaded = store.load()

            self.assertEqual(len(loaded.recent_history), 1)
            self.assertEqual(loaded.recent_history[0].time, "x")
            self.assertEqual(loaded.recent_history[0].video_id, "")
