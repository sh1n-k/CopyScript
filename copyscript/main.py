from __future__ import annotations

import argparse
from collections.abc import Sequence

from copyscript.app.logging_setup import setup_logging
from copyscript.app.runtime_options import RuntimeOptions
from copyscript.ui.window import AppWindow


def parse_runtime_options(argv: Sequence[str] | None = None) -> RuntimeOptions:
    parser = argparse.ArgumentParser(description="CopyScript desktop app")
    parser.add_argument("--hidden", action="store_true", help="Start minimized to the tray")
    args, _unknown = parser.parse_known_args(list(argv) if argv is not None else None)
    return RuntimeOptions(start_hidden=bool(args.hidden))


def main(argv: Sequence[str] | None = None) -> None:
    setup_logging()
    AppWindow(runtime_options=parse_runtime_options(argv)).run()


if __name__ == "__main__":
    main()
