from __future__ import annotations
import platform
import subprocess
from dataclasses import dataclass


@dataclass
class Notifier:
    app_name: str = "CopyScript"

    def notify(self, title: str, message: str) -> None:
        system = platform.system()
        if system == "Windows":
            self._notify_windows(title, message)
        elif system == "Darwin":
            self._notify_macos(title, message)
        else:
            # 요구사항 범위 밖(OS: Linux 등)에서는 조용히 무시
            return

    def _notify_windows(self, title: str, message: str) -> None:
        # win11toast는 Windows에서만 설치/사용하도록 지연 import
        try:
            from win11toast import toast  # type: ignore
        except Exception:
            # 패키지 미설치 등
            return
        try:
            # title, message 둘 다 지원
            toast(title, message)
        except Exception:
            # 알림 센터/집중 지원 등으로 표시되지 않을 수 있음
            return

    def _notify_macos(self, title: str, message: str) -> None:
        # osascript로 Notification Center 알림
        # 따옴표/역슬래시 이스케이프 처리
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_msg = message.replace("\\", "\\\\").replace('"', '\\"')
        script = f'display notification "{safe_msg}" with title "{safe_title}"'
        try:
            subprocess.run(
                ["osascript", "-e", script], check=False, capture_output=True, text=True
            )
        except Exception:
            return
