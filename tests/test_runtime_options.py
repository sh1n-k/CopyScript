import unittest

from copyscript.main import parse_runtime_options
from copyscript.ui.window import should_hide_on_start


class RuntimeOptionsTest(unittest.TestCase):
    def test_hidden_flag_enables_hidden_start(self):
        options = parse_runtime_options(["--hidden"])

        self.assertTrue(options.start_hidden)
        self.assertTrue(should_hide_on_start("Windows", options.start_hidden))

    def test_unknown_system_args_are_ignored(self):
        options = parse_runtime_options(["-psn_0_12345"])

        self.assertFalse(options.start_hidden)

    def test_windows_manual_start_keeps_window_visible(self):
        options = parse_runtime_options([])

        self.assertFalse(options.start_hidden)
        self.assertFalse(should_hide_on_start("Windows", options.start_hidden))

    def test_macos_always_starts_hidden(self):
        self.assertTrue(should_hide_on_start("Darwin", False))
