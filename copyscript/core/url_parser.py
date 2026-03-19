from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

YOUTUBE_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url: str) -> str | None:
    if not url or not isinstance(url, str):
        return None
    clean_url = url.strip()
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, clean_url)
        if match:
            return match.group(1)
    try:
        parsed = urlparse(clean_url)
        if "youtube.com" in parsed.netloc:
            query_params = parse_qs(parsed.query)
            if "v" in query_params:
                video_id = query_params["v"][0]
                if len(video_id) == 11:
                    return video_id
    except Exception:
        pass
    return None


def is_youtube_url(url: str) -> bool:
    return extract_video_id(url) is not None
