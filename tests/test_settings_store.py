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

    def test_corrupt_file_is_preserved_as_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingsStore()
            store.settings_path = Path(tmp) / "settings.json"
            store.settings_path.write_text("{ this is not valid json", encoding="utf-8")

            loaded = store.load()

            # 손상 파일은 기본값으로 폴백하되 원본을 .bak으로 보존한다(무경고 소실 방지).
            self.assertEqual(loaded.lang_code, AppSettings().lang_code)
            backup = store.settings_path.with_name(store.settings_path.name + ".bak")
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(encoding="utf-8"), "{ this is not valid json")

    def test_save_is_atomic_and_leaves_no_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingsStore()
            store.settings_path = Path(tmp) / "settings.json"
            store.save(AppSettings(lang_code="en"))
            store.save(AppSettings(lang_code="ko"))

            # 교체 후 임시 파일이 남지 않고, 결과 파일은 유효한 JSON이어야 한다.
            leftovers = [p.name for p in Path(tmp).iterdir() if p.name != "settings.json"]
            self.assertEqual(leftovers, [])
            import json

            data = json.loads(store.settings_path.read_text(encoding="utf-8"))
            self.assertEqual(data["lang_code"], "ko")
