import unittest
from typing import Any

from copyscript.core.subtitle_fetcher import SubtitleFetcher


class DummyTranscriptApi:
    def list(self, video_id: str) -> Any:
        return object()


class SubtitleFetcherTest(unittest.TestCase):
    def test_default_language_uses_video_default(self):
        fetcher = SubtitleFetcher(api=DummyTranscriptApi())

        self.assertEqual(fetcher.get_options().lang_code, "video-default")


if __name__ == "__main__":
    unittest.main()
