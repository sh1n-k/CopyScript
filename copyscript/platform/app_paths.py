from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

from copyscript.config.constants import APP_DATA_DIR_NAME


def get_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Local"
        data_dir = base / APP_DATA_DIR_NAME
    else:
        data_dir = Path.home() / "Library" / "Application Support" / APP_DATA_DIR_NAME
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


def get_resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def get_icon_path() -> Path:
    return get_resource_dir() / "CopyScript.ico"
