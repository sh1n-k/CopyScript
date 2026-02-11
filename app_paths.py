"""앱 데이터 경로 관리"""

from pathlib import Path

APP_NAME = "YTSubtitleCopy"


def get_data_dir() -> Path:
    """앱 설정/데이터 디렉토리 반환. 없으면 생성."""
    data_dir = Path.home() / "Library" / "Application Support" / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_settings_path() -> Path:
    return get_data_dir() / "app_settings.json"


def get_cache_dir() -> Path:
    cache_dir = get_data_dir() / "subtitle_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_items_dir() -> Path:
    items_dir = get_cache_dir() / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    return items_dir


def get_cache_index_path() -> Path:
    return get_cache_dir() / "index.json"
