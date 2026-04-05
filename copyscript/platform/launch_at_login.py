from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path

from copyscript.config.constants import (
    WINDOWS_RUN_KEY_PATH,
    WINDOWS_RUN_VALUE_NAME,
    WINDOWS_STARTUP_DELAY_MS,
    WINDOWS_STARTUP_SCRIPT_NAME,
    WINDOWS_STARTUP_SUBDIR,
)

logger = logging.getLogger(__name__)


def supports_launch_at_login() -> bool:
    return platform.system() == "Windows"


def build_launch_command(executable_path: str | None = None) -> str:
    if executable_path:
        return f'"{executable_path}" --hidden'

    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --hidden'

    script_path = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else _default_script_path()
    return f'"{Path(sys.executable).resolve()}" "{script_path}" --hidden'


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

    if get_startup_script_path().exists():
        return True

    return _has_legacy_run_key_value()


def set_launch_at_login(enabled: bool, executable_path: str | None = None) -> bool:
    if not supports_launch_at_login():
        return False

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


def _default_script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "main.py"


def _has_legacy_run_key_value() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, WINDOWS_RUN_VALUE_NAME)
            return bool(str(value).strip())
    except FileNotFoundError:
        return False
    except OSError:
        return False


def _delete_legacy_run_key_value(winreg_module) -> None:
    try:
        with winreg_module.CreateKey(winreg_module.HKEY_CURRENT_USER, WINDOWS_RUN_KEY_PATH) as key:
            try:
                winreg_module.DeleteValue(key, WINDOWS_RUN_VALUE_NAME)
            except FileNotFoundError:
                pass
    except OSError:
        logger.warning("Failed to remove legacy Run key entry", exc_info=True)
