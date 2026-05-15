import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from copyscript.platform import launch_at_login


class LaunchAtLoginTest(unittest.TestCase):
    @patch("copyscript.platform.launch_at_login.platform.system", return_value="Windows")
    def test_build_launch_command_for_script_mode(self, _system):
        with patch.object(sys, "argv", ["main.py"]):
            command = launch_at_login.build_launch_command()

        self.assertIn("--hidden", command)
        self.assertIn("main.py", command)

    @patch("copyscript.platform.launch_at_login.platform.system", return_value="Windows")
    def test_set_launch_at_login_creates_startup_script(self, _system):
        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=1,
            REG_SZ=1,
            CreateKey=MagicMock(),
            OpenKey=MagicMock(),
            DeleteValue=MagicMock(),
            QueryValueEx=MagicMock(return_value=('\"C:\\\\Programs\\\\CopyScript.exe\" --hidden', 1)),
        )
        fake_key = MagicMock()
        fake_winreg.CreateKey.return_value.__enter__.return_value = fake_key
        fake_winreg.OpenKey.return_value.__enter__.return_value = fake_key

        with tempfile.TemporaryDirectory() as temp_dir:
            startup_script_path = Path(temp_dir) / "CopyScript Startup.vbs"
            with patch.dict(sys.modules, {"winreg": fake_winreg}), patch(
                "copyscript.platform.launch_at_login.get_startup_script_path",
                return_value=startup_script_path,
            ):
                result = launch_at_login.set_launch_at_login(
                    True,
                    executable_path="C:\\Programs\\CopyScript.exe",
                )
                enabled = launch_at_login.is_launch_at_login_enabled()
                self.assertTrue(startup_script_path.exists())
                script_content = startup_script_path.read_text(encoding="utf-16")

        self.assertTrue(result)
        self.assertTrue(enabled)
        self.assertIn("WScript.Sleep 15000", script_content)
        self.assertIn('shell.Run """C:\\Programs\\CopyScript.exe"" --hidden", 0, False', script_content)
        fake_winreg.DeleteValue.assert_called_once()

    @patch("copyscript.platform.launch_at_login.platform.system", return_value="Windows")
    def test_disable_launch_at_login_deletes_value(self, _system):
        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=1,
            REG_SZ=1,
            CreateKey=MagicMock(),
            DeleteValue=MagicMock(),
        )
        fake_key = MagicMock()
        fake_winreg.CreateKey.return_value.__enter__.return_value = fake_key

        with tempfile.TemporaryDirectory() as temp_dir:
            startup_script_path = Path(temp_dir) / "CopyScript Startup.vbs"
            startup_script_path.write_text("test", encoding="utf-16")
            with patch.dict(sys.modules, {"winreg": fake_winreg}), patch(
                "copyscript.platform.launch_at_login.get_startup_script_path",
                return_value=startup_script_path,
            ):
                result = launch_at_login.set_launch_at_login(False)

        self.assertTrue(result)
        self.assertFalse(startup_script_path.exists())
        fake_winreg.DeleteValue.assert_called_once()

    @patch("copyscript.platform.launch_at_login.platform.system", return_value="Windows")
    def test_is_launch_at_login_enabled_when_startup_script_exists(self, _system):
        with tempfile.TemporaryDirectory() as temp_dir:
            startup_script_path = Path(temp_dir) / "CopyScript Startup.vbs"
            startup_script_path.write_text("test", encoding="utf-16")

            with patch(
                "copyscript.platform.launch_at_login.get_startup_script_path",
                return_value=startup_script_path,
            ):
                self.assertTrue(launch_at_login.is_launch_at_login_enabled())

    @patch("copyscript.platform.launch_at_login.platform.system", return_value="Linux")
    def test_set_launch_at_login_creates_linux_desktop_entry(self, _system):
        with tempfile.TemporaryDirectory() as temp_dir:
            autostart_path = Path(temp_dir) / "CopyScript.desktop"
            with patch(
                "copyscript.platform.launch_at_login.get_linux_autostart_path",
                return_value=autostart_path,
            ):
                result = launch_at_login.set_launch_at_login(
                    True,
                    executable_path="/home/me/.local/share/CopyScript/CopyScript",
                )
                enabled = launch_at_login.is_launch_at_login_enabled()

            content = autostart_path.read_text(encoding="utf-8")

        self.assertTrue(result)
        self.assertTrue(enabled)
        self.assertIn("Type=Application", content)
        self.assertIn('Exec="/home/me/.local/share/CopyScript/CopyScript" --hidden', content)

    @patch("copyscript.platform.launch_at_login.platform.system", return_value="Linux")
    def test_disable_launch_at_login_deletes_linux_desktop_entry(self, _system):
        with tempfile.TemporaryDirectory() as temp_dir:
            autostart_path = Path(temp_dir) / "CopyScript.desktop"
            autostart_path.write_text("test", encoding="utf-8")
            with patch(
                "copyscript.platform.launch_at_login.get_linux_autostart_path",
                return_value=autostart_path,
            ):
                result = launch_at_login.set_launch_at_login(False)

        self.assertTrue(result)
        self.assertFalse(autostart_path.exists())
