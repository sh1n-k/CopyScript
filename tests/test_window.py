import queue
import types
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from copyscript.ui.window import AppWindow


class AppWindowThreadDispatchTest(unittest.TestCase):
    def test_run_on_ui_thread_queues_windows_tray_callbacks_from_background_thread(
        self,
    ):
        window = AppWindow.__new__(AppWindow)
        window.root = MagicMock()
        window._ui_thread_id = 100
        window._ui_action_queue = queue.Queue()
        received = []

        with (
            patch("copyscript.ui.window.IS_WINDOWS", True),
            patch("copyscript.ui.window.threading.get_ident", return_value=200),
        ):
            window._run_on_ui_thread(lambda value: received.append(value), "queued")

        window.root.winfo_exists.assert_not_called()
        window.root.after.assert_not_called()
        callback, args = window._ui_action_queue.get_nowait()
        callback(*args)
        self.assertEqual(received, ["queued"])

    def test_drain_ui_actions_runs_pending_callbacks_and_reschedules(self):
        window = AppWindow.__new__(AppWindow)
        window.root = MagicMock()
        window.root.winfo_exists.return_value = True
        window._ui_action_queue = queue.Queue()
        received = []
        window._ui_action_queue.put((lambda value: received.append(value), ("first",)))
        window._ui_action_queue.put((lambda value: received.append(value), ("second",)))

        window._drain_ui_actions()

        self.assertEqual(received, ["first", "second"])
        window.root.after.assert_called_once_with(50, window._drain_ui_actions)

    def test_queue_status_uses_windows_ui_queue_from_background_thread(self):
        window = AppWindow.__new__(AppWindow)
        window.root = MagicMock()
        window._ui_thread_id = 100
        window._ui_action_queue = queue.Queue()
        window.status_panel = MagicMock()

        with (
            patch("copyscript.ui.window.IS_WINDOWS", True),
            patch("copyscript.ui.window.threading.get_ident", return_value=200),
        ):
            window._queue_status("running", False)

        window.root.winfo_exists.assert_not_called()
        window.status_panel.set_status.assert_not_called()
        callback, args = window._ui_action_queue.get_nowait()
        callback(*args)
        window.status_panel.set_status.assert_called_once_with("running", False)

    def test_run_on_ui_thread_queues_linux_tray_callbacks_from_background_thread(self):
        window = AppWindow.__new__(AppWindow)
        window.root = MagicMock()
        window._ui_thread_id = 100
        window._ui_action_queue = queue.Queue()
        received = []

        with (
            patch("copyscript.ui.window.HAS_TRAY", True),
            patch("copyscript.ui.window.threading.get_ident", return_value=200),
        ):
            window._run_on_ui_thread(lambda value: received.append(value), "queued")

        window.root.winfo_exists.assert_not_called()
        callback, args = window._ui_action_queue.get_nowait()
        callback(*args)
        self.assertEqual(received, ["queued"])

    def test_setup_tray_shows_window_when_hidden_start_fails(self):
        window = AppWindow.__new__(AppWindow)
        window.root = MagicMock()
        window._start_hidden = True
        window.__dict__["controller"] = types.SimpleNamespace(
            toggle_monitoring=MagicMock(),
            settings=types.SimpleNamespace(lang_code="ko", include_timestamp=False),
            is_running=False,
        )
        window._run_on_ui_thread = MagicMock()
        window._tray_on_language = MagicMock()
        window._tray_on_timestamp = MagicMock()
        window._show_window = MagicMock()
        window._quit = MagicMock()
        window.status_ui = None

        fake_tray_module = types.SimpleNamespace()

        def raise_tray_error(*args, **kwargs):
            del args, kwargs
            raise RuntimeError("tray failed")

        fake_tray_module.TrayController = raise_tray_error

        with patch.dict("sys.modules", {"copyscript.platform.tray": fake_tray_module}):
            window._setup_tray()

        self.assertIsNone(window.status_ui)
        window._show_window.assert_called_once_with()
