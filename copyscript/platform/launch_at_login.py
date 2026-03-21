from __future__ import annotations

import platform
import sys
from pathlib import Path

from copyscript.config.constants import WINDOWS_RUN_KEY_PATH, WINDOWS_RUN_VALUE_NAME


def supports_launch_at_login() -> bool:
    return platform.system() == "Windows"


def build_launch_command(executable_path: str | None = None) -> str:
    if executable_path:
        return f'"{executable_path}" --hidden'

    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --hidden'

    script_path = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else _default_script_path()
    return f'"{Path(sys.executable).resolve()}" "{script_path}" --hidden'


def is_launch_at_login_enabled() -> bool:
    if not supports_launch_at_login():
        return False

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, WINDOWS_RUN_VALUE_NAME)
            return bool(str(value).strip())
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_launch_at_login(enabled: bool, executable_path: str | None = None) -> bool:
    if not supports_launch_at_login():
        return False

    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY_PATH) as key:
            if enabled:
                winreg.SetValueEx(key, WINDOWS_RUN_VALUE_NAME, 0, winreg.REG_SZ, build_launch_command(executable_path))
            else:
                try:
                    winreg.DeleteValue(key, WINDOWS_RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def _default_script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "main.py"
