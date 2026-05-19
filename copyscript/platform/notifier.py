from __future__ import annotations

import logging
import platform
import subprocess
from dataclasses import dataclass

from copyscript.config.constants import APP_NAME

logger = logging.getLogger(__name__)


@dataclass
class Notifier:
    app_name: str = APP_NAME

    def notify(self, title: str, message: str) -> None:
        system = platform.system()
        if system == "Windows":
            self._notify_windows(title, message)
            return
        if system == "Darwin":
            self._notify_macos(title, message)

    def _notify_windows(self, title: str, message: str) -> None:
        try:
            from win11toast import toast  # type: ignore
        except ImportError:
            logger.debug("win11toast is not available")
            return
        try:
            toast(title, message)
        except Exception:
            logger.debug("Windows notification failed", exc_info=True)
            return

    def _notify_macos(self, title: str, message: str) -> None:
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
        script = f'display notification "{safe_message}" with title "{safe_title}"'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            logger.debug("macOS notification failed", exc_info=True)
            return
