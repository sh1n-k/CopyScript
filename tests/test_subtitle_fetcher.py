import unittest

from copyscript.core.subtitle_fetcher import SubtitleFetcher


class SubtitleFetcherTest(unittest.TestCase):
    def test_default_language_uses_video_default(self):
        fetcher = SubtitleFetcher(api=object())

        self.assertEqual(fetcher.get_options().lang_code, "video-default")


if __name__ == "__main__":
    unittest.main()
