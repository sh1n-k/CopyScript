# Architecture Overhaul Status

## What Changed

- Runtime code now lives under `copyscript/`.
- `copyscript/app/` handles settings persistence and runtime lifecycle.
- `copyscript/core/` handles URL parsing, subtitle fetching, cache, and clipboard processing.
- `copyscript/platform/` handles app paths, notifications, clipboard watchers, and macOS menubar integration.
- `copyscript/ui/` handles the Tk window, panels, and theme.
- Root modules remain as compatibility wrappers.

## Verified

- `python3 -m unittest discover -s tests -v`
- `python3 -m compileall .`
- Python LSP diagnostics: 0 errors
- `".venv/bin/python" -c "from copyscript.app.controller import AppController; AppController(); print('controller-ok')"`
- `".venv-tk/bin/python" -c "import main; import copyscript.main; print('entrypoints-ok')"`

## Environment Blockers

- Homebrew Python 3.12-3.14 on this machine does not provide `_tkinter`, so real Tk startup cannot be verified there.
- System Python can load Tk, but the available `pyobjc` runtime combination currently errors with `macOS 26 (2603) or later required, have instead 16 (1603)!` during macOS UI startup.
- Because of that, non-UI and import paths are verified, but a full local macOS menubar/window smoke test is still blocked by environment compatibility.

## Recommended Commit Split

1. Package structure and compatibility wrappers
   - `.gitignore`
   - `main.py`
   - `app_paths.py`
   - `clipboard_monitor.py`
   - `clipboard_watchers.py`
   - `menubar.py`
   - `notifier.py`
   - `subtitle_cache.py`
   - `subtitle_fetcher.py`
   - `url_parser.py`
   - `copyscript/config/*`
   - `copyscript/core/*`
   - `copyscript/platform/*`
   Justification: these files define the new package boundary and preserve old import paths.

2. Lifecycle and UI decomposition
   - `copyscript/app/*`
   - `copyscript/ui/*`
   Justification: these files move orchestration and view composition out of the old monolithic entrypoint.

3. Test updates for the new contracts
   - `tests/test_clipboard_monitor.py`
   - `tests/test_app_paths.py`
   - `tests/test_settings_store.py`
   Justification: these files validate the new settings, path, and processing-option behavior.

4. Documentation and build entrypoint updates
   - `README.md`
   - `CLAUDE.md`
   - `AGENTS.md`
   - `build.sh`
   Justification: these files document the new structure and align packaging with the new entrypoint.

## Next Commands

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall .
GIT_MASTER=1 git status
```
