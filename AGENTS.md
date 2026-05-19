# AGENTS.md

## Project Overview
- This repository contains `CopyScript`, a desktop app that watches clipboard changes and replaces copied YouTube URLs with transcript text.
- Primary runtime targets are macOS and Windows.
- Main success condition for agent tasks: keep clipboard-processing behavior stable and avoid breaking startup/install flows.

## Setup Commands
- Sync environment: `uv sync --group dev`
- Run app (dev): `uv run python -m copyscript`
- Build macOS app: `./scripts/build/build.sh`
- Install built app + LaunchAgent: `./scripts/install/install.sh`
- Uninstall app: `./scripts/install/uninstall.sh`

## Test Commands
- Lint (preferred): `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Type check: `uv run pyright`
- If `ruff` is unavailable, run at least syntax validation: `python -m compileall .`
- Unit tests: `uv run pytest`
- E2E (startup/install path on macOS):
  - `./scripts/build/build.sh`
  - `./scripts/install/install.sh`
  - `launchctl print gui/$(id -u)/com.ytsubtitlecopy.app`
  - `launchctl kickstart -k gui/$(id -u)/com.ytsubtitlecopy.app`
  - `pgrep -fl "CopyScript|YouTube 자막 복사"`

## Project Structure
- `copyscript/app/`: settings persistence and runtime lifecycle.
- `copyscript/config/`: shared constants, language definitions, dataclasses.
- `copyscript/core/`: URL parsing, transcript fetch, cache, clipboard pipeline.
- `copyscript/platform/`: OS-specific paths, watchers, notifications, macOS menubar.
- `copyscript/ui/`: Tkinter window, panels, theme.
- `scripts/build/`: PyInstaller build scripts.
- `scripts/install/`: install and uninstall scripts.
- `packaging/pyinstaller/`: PyInstaller spec.
- `tests/`: unit tests.

## Code Style And Conventions
- Use Python 3.10+ type hints.
- Keep identifiers in English (`snake_case` for functions/variables, `PascalCase` for classes).
- Keep UI strings and comments in Korean unless there is a strong reason not to.
- GUI updates from watcher callbacks must stay thread-safe.
- On Windows, tray/watcher callbacks must use `AppWindow._run_on_ui_thread(...)` and the internal UI queue instead of touching Tk directly.
- On macOS, keep the existing menubar/Tk callback behavior unless there is a platform-specific reason to change it.

## Safety / Security
- Do not commit secrets, tokens, or personal machine paths.
- Avoid destructive commands unless explicitly requested.
- Before running commands with destructive effects (for example `rm -rf` in install/uninstall scripts), confirm scope and intent.
- Preserve existing user data path compatibility unless migration is explicitly requested (`~/Library/Application Support/CopyScript`).
