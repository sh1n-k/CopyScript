# CopyScript

## Run
- `uv sync --group dev`
- `uv run python main.py`

## Verify
- `uv run ruff check .`
- `uv run pytest`
- fallback: `python3 -m unittest discover -s tests -v`
- fallback: `python3 -m compileall .`

## Build
- `./build.sh`
- `./install.sh`
- `./uninstall.sh`

## Architecture
- Runtime code lives in `copyscript/`.
- `copyscript/app/`: settings persistence and lifecycle orchestration.
- `copyscript/core/`: transcript pipeline, cache, URL parsing.
- `copyscript/platform/`: OS-specific paths, notifications, watchers, macOS menubar.
- `copyscript/ui/`: Tk window, panels, theme.
- Root modules are compatibility wrappers; prefer editing package modules.

## Multi-file Rules
- Settings changes must keep `ProcessingOptions`, cache invalidation, and processed-id reset in sync.
- GUI updates from watcher callbacks must stay on `root.after(...)`.
- Preserve data-path compatibility for macOS: `~/Library/Application Support/YTSubtitleCopy`.
- Large refactors should use a dedicated feature branch + worktree under `.worktrees/`.
