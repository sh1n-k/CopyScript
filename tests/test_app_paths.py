import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from copyscript.platform import app_paths


class AppPathsTest(unittest.TestCase):
    def test_macos_path_uses_app_name_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch(
                "copyscript.platform.app_paths.platform.system", return_value="Darwin"
            ):
                with patch("pathlib.Path.home", return_value=home):
                    path = app_paths.get_data_dir()

            self.assertEqual(
                path, home / "Library" / "Application Support" / "CopyScript"
            )

    def test_windows_path_uses_localappdata(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with patch(
                "copyscript.platform.app_paths.platform.system", return_value="Windows"
            ):
                with patch.dict(os.environ, {"LOCALAPPDATA": str(base)}, clear=False):
                    path = app_paths.get_data_dir()

            self.assertEqual(path, base / "CopyScript")

    def test_linux_path_uses_xdg_data_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with patch(
                "copyscript.platform.app_paths.platform.system", return_value="Linux"
            ):
                with patch.dict(os.environ, {"XDG_DATA_HOME": str(base)}, clear=False):
                    path = app_paths.get_data_dir()

            self.assertEqual(path, base / "CopyScript")
