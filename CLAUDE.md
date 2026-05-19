# CopyScript

## Run
- `uv sync --group dev`
- `uv run python -m copyscript`

## Verify
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pyright`
- `uv run pytest`
- fallback: `python3 -m unittest discover -s tests -v`
- fallback: `python3 -m compileall .`

## Build
- `./scripts/build/build.sh`
- `./scripts/install/install.sh`
- `./scripts/install/uninstall.sh`

## Architecture
- Runtime code lives in `copyscript/`.
- `copyscript/app/`: settings persistence and lifecycle orchestration.
- `copyscript/core/`: transcript pipeline, cache, URL parsing.
- `copyscript/platform/`: OS-specific paths, notifications, watchers, macOS menubar.
- `copyscript/ui/`: Tk window, panels, theme.
- `scripts/`: build, install, and uninstall scripts.
- `packaging/pyinstaller/`: PyInstaller spec.

## Multi-file Rules
- Settings changes must keep `ProcessingOptions`, cache invalidation, and processed-id reset in sync.
- GUI updates from watcher callbacks must stay thread-safe.
- On Windows, tray/watcher callbacks must go through `AppWindow._run_on_ui_thread(...)` and the UI queue rather than touching Tk objects directly.
- Preserve data-path compatibility for macOS: `~/Library/Application Support/CopyScript`.
- Large refactors should use a dedicated feature branch + worktree under `.worktrees/`.
