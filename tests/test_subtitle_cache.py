import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from copyscript.core.subtitle_cache import SubtitleCache


class SubtitleCacheTest(unittest.TestCase):
    def test_lru_eviction_respects_recent_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache = SubtitleCache(
                max_items=2,
                index_path=base / "index.json",
                items_dir=base / "items",
            )

            cache.put("v1", "ko", False, "line 1")
            cache.put("v2", "ko", False, "line 2")

            # v1을 최근 접근 처리해서 v2가 먼저 축출되도록 유도
            self.assertEqual(cache.get("v1", "ko", False), "line 1")

            cache.put("v3", "ko", False, "line 3")

            self.assertIsNone(cache.get("v2", "ko", False))
            self.assertEqual(cache.get("v1", "ko", False), "line 1")
            self.assertEqual(cache.get("v3", "ko", False), "line 3")

    def test_clear_all_removes_all_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache = SubtitleCache(
                max_items=5,
                index_path=base / "index.json",
                items_dir=base / "items",
            )
            cache.put("v1", "ko", False, "one")
            cache.put("v2", "en", True, "two")

            cache.clear_all()

            self.assertIsNone(cache.get("v1", "ko", False))
            self.assertIsNone(cache.get("v2", "en", True))

    def test_stats_reports_utilization_and_recent_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache = SubtitleCache(
                max_items=3,
                index_path=base / "index.json",
                items_dir=base / "items",
            )
            cache.put("v1", "ko", False, "a\nb")
            cache.put("v2", "en", True, "c")
            # v1 재접근 후 v3 저장 -> recent 순서: v3, v1, v2
            self.assertEqual(cache.get("v1", "ko", False), "a\nb")
            cache.put("v3", "ko", False, "d\ne\nf")

            stats = cache.stats()
            self.assertEqual(stats["item_count"], 3)
            self.assertEqual(stats["max_items"], 3)
            self.assertEqual(stats["utilization_pct"], 100)
            self.assertGreaterEqual(stats["total_lines"], 6)
            self.assertEqual(stats["entries_recent"][0]["video_id"], "v3")

    def test_stats_uses_cached_metadata_without_reading_item_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache = SubtitleCache(
                max_items=3,
                index_path=base / "index.json",
                items_dir=base / "items",
            )
            cache.put("v1", "ko", False, "가\n나")
            cache.put("v2", "en", True, "abc")

            with patch.object(Path, "read_text", side_effect=AssertionError("unexpected read")):
                stats = cache.stats()

            self.assertEqual(stats["total_chars"], 6)
            self.assertEqual(stats["total_lines"], 3)
            self.assertGreater(stats["total_bytes"], 0)

    def test_legacy_cache_index_hydrates_metadata_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            items_dir = base / "items"
            items_dir.mkdir()
            (items_dir / "legacy.txt").write_text("one\ntwo", encoding="utf-8")
            (base / "index.json").write_text(
                json.dumps(
                    {
                        "max_items": 5,
                        "entries": [
                            {
                                "key": "v1|ko|0",
                                "video_id": "v1",
                                "lang_code": "ko",
                                "include_timestamp": False,
                                "file_name": "legacy.txt",
                                "line_count": 0,
                                "updated_at": "old",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            cache = SubtitleCache(
                max_items=5,
                index_path=base / "index.json",
                items_dir=items_dir,
            )

            stats = cache.stats()
            self.assertEqual(stats["total_chars"], 7)
            self.assertEqual(stats["total_lines"], 2)
            saved = json.loads((base / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["entries"][0]["char_count"], 7)
            self.assertGreater(saved["entries"][0]["byte_count"], 0)

    def test_corrupt_cache_metadata_is_rehydrated_from_item_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            items_dir = base / "items"
            items_dir.mkdir()
            (items_dir / "item.txt").write_text("fixed", encoding="utf-8")
            (base / "index.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "v1|ko|0",
                                "video_id": "v1",
                                "lang_code": "ko",
                                "include_timestamp": False,
                                "file_name": "item.txt",
                                "line_count": 1,
                                "char_count": "bad",
                                "byte_count": "bad",
                                "updated_at": "old",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            cache = SubtitleCache(
                max_items=5,
                index_path=base / "index.json",
                items_dir=items_dir,
            )

            stats = cache.stats()
            self.assertEqual(stats["item_count"], 1)
            self.assertEqual(stats["total_chars"], 5)

    def test_set_max_items_triggers_lru_eviction(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache = SubtitleCache(
                max_items=4,
                index_path=base / "index.json",
                items_dir=base / "items",
            )
            cache.put("v1", "ko", False, "one")
            cache.put("v2", "ko", False, "two")
            cache.put("v3", "ko", False, "three")

            cache.set_max_items(2)

            self.assertIsNone(cache.get("v1", "ko", False))
            self.assertEqual(cache.get("v2", "ko", False), "two")
            self.assertEqual(cache.get("v3", "ko", False), "three")


if __name__ == "__main__":
    unittest.main()
