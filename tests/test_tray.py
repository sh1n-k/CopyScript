import unittest
from unittest.mock import MagicMock, patch

from copyscript.platform.tray import TrayController


class TrayControllerTest(unittest.TestCase):
    @patch("copyscript.platform.tray.pystray.Icon")
    @patch.object(TrayController, "_load_icon_image", return_value=object())
    def test_constructor_builds_language_submenu_without_invalid_actions(self, _icon_image, icon_mock):
        icon_instance = MagicMock()
        icon_mock.return_value = icon_instance

        TrayController(
            on_toggle=lambda: None,
            on_language=lambda code: None,
            on_timestamp=lambda: None,
            on_show_settings=lambda: None,
            on_quit=lambda: None,
        )

        icon_mock.assert_called_once()
        icon_instance.run_detached.assert_called_once()
