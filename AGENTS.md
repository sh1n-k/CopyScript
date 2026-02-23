# AGENTS.md

## Project Overview
- This repository contains `CopyScript`, a desktop app that watches clipboard changes and replaces copied YouTube URLs with transcript text.
- Primary runtime targets are macOS and Windows.
- Main success condition for agent tasks: keep clipboard-processing behavior stable and avoid breaking startup/install flows.

## Setup Commands
- Create virtualenv: `python3 -m venv .venv`
- Activate virtualenv: `source .venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Run app (dev): `python main.py`
- Build macOS app: `./build.sh`
- Install built app + LaunchAgent: `./install.sh`
- Uninstall app: `./uninstall.sh`

## Test Commands
- Lint (preferred): `ruff check .`
- If `ruff` is unavailable, run at least syntax validation: `python -m compileall .`
- Unit tests: `pytest tests/`
- E2E (startup/install path on macOS):
  - `./build.sh`
  - `./install.sh`
  - `launchctl print gui/$(id -u)/com.ytsubtitlecopy.app`
  - `launchctl kickstart -k gui/$(id -u)/com.ytsubtitlecopy.app`
  - `pgrep -fl "CopyScript|YouTube 자막 복사"`

## Project Structure
- `main.py`: Tkinter app lifecycle and UI, plus macOS menubar integration.
- `menubar.py`: macOS `NSStatusItem` menu controller.
- `clipboard_monitor.py`: URL detection and transcript copy pipeline.
- `clipboard_watchers.py`: platform clipboard change watchers.
- `subtitle_fetcher.py`: transcript retrieval and language fallback.
- `subtitle_cache.py`: local LRU cache.
- `install.sh` / `uninstall.sh`: macOS install, LaunchAgent registration, removal.
- `tests/`: pytest unit tests.

## Code Style And Conventions
- Use Python 3.10+ type hints.
- Keep identifiers in English (`snake_case` for functions/variables, `PascalCase` for classes).
- Keep UI strings and comments in Korean unless there is a strong reason not to.
- GUI updates from watcher callbacks must stay thread-safe via `root.after(...)`.

## Safety / Security
- Do not commit secrets, tokens, or personal machine paths.
- Avoid destructive commands unless explicitly requested.
- Before running commands with destructive effects (for example `rm -rf` in install/uninstall scripts), confirm scope and intent.
- Preserve existing user data path compatibility unless migration is explicitly requested (`~/Library/Application Support/YTSubtitleCopy`).
