import unittest

from copyscript.core.url_parser import extract_video_id, is_youtube_url


class UrlParserTest(unittest.TestCase):
    def test_extracts_supported_youtube_url_formats(self):
        cases = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/embed/dQw4w9WgXcQ",
            "https://youtube.com/v/dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ]

        for url in cases:
            with self.subTest(url=url):
                self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_rejects_non_youtube_urls(self):
        self.assertIsNone(extract_video_id("https://example.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(is_youtube_url("not a youtube url"))


if __name__ == "__main__":
    unittest.main()
