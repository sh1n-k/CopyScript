import sys
import types
import unittest
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
    def test_set_launch_at_login_writes_run_key(self, _system):
        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=1,
            REG_SZ=1,
            CreateKey=MagicMock(),
            OpenKey=MagicMock(),
            SetValueEx=MagicMock(),
            DeleteValue=MagicMock(),
            QueryValueEx=MagicMock(return_value=('\"C:\\\\Programs\\\\CopyScript.exe\" --hidden', 1)),
        )
        fake_key = MagicMock()
        fake_winreg.CreateKey.return_value.__enter__.return_value = fake_key
        fake_winreg.OpenKey.return_value.__enter__.return_value = fake_key

        with patch.dict(sys.modules, {"winreg": fake_winreg}):
            result = launch_at_login.set_launch_at_login(True, executable_path="C:\\Programs\\CopyScript.exe")
            enabled = launch_at_login.is_launch_at_login_enabled()

        self.assertTrue(result)
        self.assertTrue(enabled)
        fake_winreg.SetValueEx.assert_called_once()

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

        with patch.dict(sys.modules, {"winreg": fake_winreg}):
            result = launch_at_login.set_launch_at_login(False)

        self.assertTrue(result)
        fake_winreg.DeleteValue.assert_called_once()
