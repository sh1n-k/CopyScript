from __future__ import annotations

import faulthandler
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import threading
from pathlib import Path

from copyscript.platform.app_paths import get_data_dir

_LOG_INITIALIZED = False
_FAULT_LOG_STREAM = None


def get_log_path() -> Path:
    return get_data_dir() / "copyscript.log"


def setup_logging() -> Path:
    global _LOG_INITIALIZED
    global _FAULT_LOG_STREAM

    log_path = get_log_path()
    if _LOG_INITIALIZED:
        return log_path

    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=512 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    _FAULT_LOG_STREAM = open(log_path, "a", encoding="utf-8")
    faulthandler.enable(file=_FAULT_LOG_STREAM, all_threads=True)

    def _log_unhandled_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            logging.getLogger("copyscript.crash").info(
                "Process interrupted: %s",
                exc_type.__name__,
            )
            return
        logging.getLogger("copyscript.crash").exception(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    def _log_thread_exception(args) -> None:
        if issubclass(args.exc_type, (KeyboardInterrupt, SystemExit)):
            logging.getLogger("copyscript.crash").info(
                "Thread interrupted: %s (%s)",
                args.exc_type.__name__,
                args.thread.name if args.thread else "unknown-thread",
            )
            return
        logging.getLogger("copyscript.crash").exception(
            "Unhandled thread exception in %s",
            args.thread.name if args.thread else "unknown-thread",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _log_unhandled_exception
    threading.excepthook = _log_thread_exception
    logging.getLogger(__name__).info(
        "Logging initialized at %s (pid=%s, platform=%s)",
        log_path,
        os.getpid(),
        sys.platform,
    )
    _LOG_INITIALIZED = True
    return log_path
