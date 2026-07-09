from __future__ import annotations

import logging
import os
import platform
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

from copyscript.config.constants import (
    APP_NAME,
    LINUX_AUTOSTART_FILENAME,
    WINDOWS_RUN_KEY_PATH,
    WINDOWS_RUN_VALUE_NAME,
    WINDOWS_STARTUP_DELAY_MS,
    WINDOWS_STARTUP_SCRIPT_NAME,
    WINDOWS_STARTUP_SUBDIR,
)

logger = logging.getLogger(__name__)


def supports_launch_at_login() -> bool:
    return platform.system() in {"Windows", "Linux"}


def build_launch_command(executable_path: str | None = None) -> str:
    if executable_path:
        return f'"{executable_path}" --hidden'

    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --hidden'

    if platform.system() == "Windows":
        project_root = Path(__file__).resolve().parents[2]
        python_path = Path(sys.executable).resolve()
        return (
            f'cmd /c cd /d "{project_root}" && "{python_path}" -m copyscript --hidden'
        )

    project_root = Path(__file__).resolve().parents[2]
    python_path = Path(sys.executable).resolve()
    return (
        f'/bin/sh -lc \'cd "{project_root}" && "{python_path}" -m copyscript --hidden\''
    )


def get_startup_script_path() -> Path:
    appdata = os.environ.get("APPDATA")
    base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base_dir / WINDOWS_STARTUP_SUBDIR / WINDOWS_STARTUP_SCRIPT_NAME


def build_startup_script(command: str, delay_ms: int = WINDOWS_STARTUP_DELAY_MS) -> str:
    escaped_command = command.replace('"', '""')
    return "\r\n".join(
        [
            'Set shell = CreateObject("WScript.Shell")',
            f"WScript.Sleep {max(0, int(delay_ms))}",
            f'shell.Run "{escaped_command}", 0, False',
            "",
        ]
    )


def is_launch_at_login_enabled() -> bool:
    if not supports_launch_at_login():
        return False
    if platform.system() == "Linux":
        return get_linux_autostart_path().exists()

    if get_startup_script_path().exists():
        return True

    return _has_legacy_run_key_value()


def set_launch_at_login(enabled: bool, executable_path: str | None = None) -> bool:
    if not supports_launch_at_login():
        return False
    if platform.system() == "Linux":
        return _set_linux_launch_at_login(enabled, executable_path)

    startup_script_path = get_startup_script_path()
    import winreg

    try:
        if enabled:
            startup_script_path.parent.mkdir(parents=True, exist_ok=True)
            startup_script_path.write_text(
                build_startup_script(build_launch_command(executable_path)),
                encoding="utf-16",
            )
        else:
            startup_script_path.unlink(missing_ok=True)
        _delete_legacy_run_key_value(winreg)
        return True
    except OSError:
        logger.exception("Failed to update launch-at-login state")
        return False
    except Exception:
        logger.exception("Unexpected failure while updating launch-at-login state")
        return False


def get_linux_autostart_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base_dir = Path(config_home) if config_home else Path.home() / ".config"
    return base_dir / "autostart" / LINUX_AUTOSTART_FILENAME


def build_linux_desktop_entry(command: str) -> str:
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            f"Name={APP_NAME}",
            f"Exec={command}",
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
            "",
        ]
    )


def _set_linux_launch_at_login(
    enabled: bool, executable_path: str | None = None
) -> bool:
    autostart_path = get_linux_autostart_path()
    try:
        if enabled:
            autostart_path.parent.mkdir(parents=True, exist_ok=True)
            autostart_path.write_text(
                build_linux_desktop_entry(build_launch_command(executable_path)),
                encoding="utf-8",
            )
        else:
            autostart_path.unlink(missing_ok=True)
        return True
    except OSError:
        logger.exception("Failed to update Linux autostart state")
        return False


def _has_legacy_run_key_value() -> bool:
    winreg: Any = import_module("winreg")

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY_PATH, 0, winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, WINDOWS_RUN_VALUE_NAME)
            return bool(str(value).strip())
    except FileNotFoundError:
        return False
    except OSError:
        return False


def _delete_legacy_run_key_value(winreg_module) -> None:
    try:
        with winreg_module.CreateKey(
            winreg_module.HKEY_CURRENT_USER, WINDOWS_RUN_KEY_PATH
        ) as key:
            try:
                winreg_module.DeleteValue(key, WINDOWS_RUN_VALUE_NAME)
            except FileNotFoundError:
                pass
    except OSError:
        logger.warning("Failed to remove legacy Run key entry", exc_info=True)
