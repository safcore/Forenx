"""Reusable logging configuration for the ForenX forensics engine.

Provides console logging plus rotating application and error log files.
Import ``get_logger`` from other modules rather than calling
``logging.getLogger`` directly.

Logging is **lazy**: importing this package does not create files or attach
console handlers. Call ``setup_logging()`` from application entry points
(e.g. ``main.py``) or host frameworks (e.g. Django).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.utils.config import (
    APPLICATION_LOG_FILE,
    ERRORS_LOG_FILE,
    LOG_BACKUP_COUNT,
    LOG_DIRECTORY,
    LOG_MAX_BYTES,
    PROJECT_NAME,
)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured: bool = False


def _ensure_log_file(path: Path) -> Path:
    """Create a log file and its parent directory if they do not exist.

    Args:
        path: Absolute path to the log file.

    Returns:
        The same ``path`` after ensuring it exists on disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    return path


def setup_logging(
    log_directory: Path | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure and return the root ForenX logger.

    Creates the log directory and required log files if missing, then
    attaches:

    - a console handler (``level`` and above)
    - a rotating application log (``application.log``)
    - a rotating error log (``errors.log``, WARNING and above)

    Args:
        log_directory: Directory for log files. Defaults to
            ``config.LOG_DIRECTORY``.
        level: Minimum logging level for console and application log
            (default: ``logging.INFO``).

    Returns:
        Configured ``logging.Logger`` instance named after the project.
    """
    global _configured

    log_dir = log_directory or LOG_DIRECTORY
    application_log = _ensure_log_file(log_dir / APPLICATION_LOG_FILE)
    errors_log = _ensure_log_file(log_dir / ERRORS_LOG_FILE)

    root_logger = logging.getLogger("forenx")
    root_logger.setLevel(level)

    # Avoid duplicate handlers when setup_logging is called more than once.
    if _configured:
        return root_logger

    # Remove placeholder NullHandler attached during lazy imports.
    root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    application_handler = RotatingFileHandler(
        filename=application_log,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    application_handler.setLevel(level)
    application_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        filename=errors_log,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(application_handler)
    root_logger.addHandler(error_handler)
    root_logger.propagate = False

    _configured = True
    root_logger.info("%s logging initialized", PROJECT_NAME)
    return root_logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under the ForenX logging hierarchy.

    Does **not** automatically configure file/console handlers. Until
    ``setup_logging()`` is called, a ``NullHandler`` is attached to the
    root ``forenx`` logger so host applications (e.g. Django) can import
    the engine without side effects.

    Args:
        name: Optional logger suffix. When provided, returns
            ``forenx.<name>``; otherwise returns the root ``forenx`` logger.

    Returns:
        A ``logging.Logger`` instance.
    """
    root_logger = logging.getLogger("forenx")
    if not _configured and not root_logger.handlers:
        root_logger.addHandler(logging.NullHandler())
        root_logger.propagate = False

    if name:
        return logging.getLogger(f"forenx.{name}")
    return root_logger


# Module-level reusable logger instance (lazy; no file I/O on import).
logger: logging.Logger = get_logger()
