"""Forensically safe SQLite helpers for browser database analysis.

Original evidence files are never opened for write access. Databases are
copied to a temporary location (including companion WAL/SHM files when
present) and queried read-only.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.utils.exceptions import BrowserHistoryError, EvidenceFileError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _companion_files(source: Path) -> list[Path]:
    """Return existing SQLite companion files for ``source``."""
    companions: list[Path] = []
    for suffix in ("-wal", "-shm", "-journal"):
        candidate = Path(str(source) + suffix)
        if candidate.is_file():
            companions.append(candidate)
    return companions


@contextmanager
def open_readonly_copy(source: Path) -> Iterator[sqlite3.Connection]:
    """Copy a SQLite database to a temp file and open it read-only.

    Args:
        source: Path to the original evidence database.

    Yields:
        A read-only ``sqlite3.Connection`` against the temporary copy.

    Raises:
        EvidenceFileError: If the source is missing or inaccessible.
        BrowserHistoryError: If the copy cannot be opened as SQLite.
    """
    if not str(source):
        raise EvidenceFileError("Browser database path must not be empty")
    if not source.exists():
        raise EvidenceFileError(f"Browser database not found: {source}")
    if not source.is_file():
        raise EvidenceFileError(f"Browser database path is not a file: {source}")

    temp_dir = Path(tempfile.mkdtemp(prefix="forenx_browser_"))
    temp_db = temp_dir / source.name

    try:
        try:
            shutil.copy2(source, temp_db)
            for companion in _companion_files(source):
                shutil.copy2(companion, temp_dir / companion.name)
            logger.info(
                "Copied browser database '%s' to temporary location for analysis",
                source.name,
            )
        except PermissionError as exc:
            raise EvidenceFileError(
                f"Permission denied while copying browser database: {source}"
            ) from exc
        except OSError as exc:
            raise BrowserHistoryError(
                f"Failed to copy browser database '{source}': {exc}"
            ) from exc

        uri = temp_db.resolve().as_uri() + "?mode=ro"
        try:
            connection = sqlite3.connect(uri, uri=True)
            connection.row_factory = sqlite3.Row
            # Touch sqlite_master to fail fast on non-SQLite files.
            connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
            logger.info("Opened temporary SQLite database read-only: %s", source.name)
        except sqlite3.Error as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise BrowserHistoryError(
                f"Corrupted or unreadable browser database '{source}': {exc}"
            ) from exc

        try:
            yield connection
        finally:
            connection.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("Cleaned temporary browser database copy for '%s'", source.name)


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Return whether ``table_name`` exists in the opened database."""
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def fetch_all(
    connection: sqlite3.Connection,
    query: str,
    params: tuple = (),
) -> list[sqlite3.Row]:
    """Execute a read-only SQL query and return all rows."""
    try:
        return list(connection.execute(query, params))
    except sqlite3.Error as exc:
        raise BrowserHistoryError(f"SQLite query failed: {exc}") from exc
