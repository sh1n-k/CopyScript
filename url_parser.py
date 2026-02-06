"""YouTube URL 파싱 및 검증 모듈"""

import re
from urllib.parse import urlparse, parse_qs

# YouTube URL 패턴
YOUTUBE_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url: str) -> str | None:
    """
    YouTube URL에서 video_id를 추출합니다.

    Args:
        url: YouTube URL 문자열

    Returns:
        11자리 video_id 또는 None
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    # 정규식 패턴 매칭
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # fallback: query parameter에서 v 추출
    try:
        parsed = urlparse(url)
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
    """URL이 유효한 YouTube URL인지 확인합니다."""
    return extract_video_id(url) is not None


if __name__ == "__main__":
    # 테스트
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "invalid url",
        "https://google.com",
    ]

    for url in test_urls:
        vid = extract_video_id(url)
        print(f"{url[:50]:50} -> {vid}")
