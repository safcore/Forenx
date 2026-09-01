"""Google Chrome offline profile artifact extraction."""

from __future__ import annotations

import json
from pathlib import Path

from app.browser.models import (
    CHROMIUM_DANGER_TYPES,
    CHROMIUM_TRANSITION_NAMES,
    BrowserType,
    chrome_timestamp_to_datetime,
    detect_search,
    extract_domain,
    is_login_page,
)
from app.browser.sqlite_reader import fetch_all, open_readonly_copy, table_exists
from app.schemas.browser import (
    BrowserArtifacts,
    BrowserBookmark,
    BrowserCookieMetadata,
    BrowserDownload,
    BrowserLoginPage,
    BrowserSearch,
    BrowserVisit,
)
from app.utils.exceptions import BrowserHistoryError, EvidenceFileError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_HISTORY_VISITS_SQL = """
SELECT
    u.url AS url,
    u.title AS title,
    u.visit_count AS visit_count,
    v.visit_time AS visit_time,
    v.transition AS transition
FROM visits AS v
JOIN urls AS u ON u.id = v.url
ORDER BY v.visit_time DESC
"""

_HISTORY_URLS_FALLBACK_SQL = """
SELECT
    url AS url,
    title AS title,
    visit_count AS visit_count,
    last_visit_time AS visit_time,
    NULL AS transition
FROM urls
ORDER BY last_visit_time DESC
"""

_DOWNLOADS_SQL = """
SELECT
    d.target_path AS target_path,
    d.current_path AS current_path,
    d.start_time AS start_time,
    d.total_bytes AS total_bytes,
    d.received_bytes AS received_bytes,
    d.danger_type AS danger_type,
    (
        SELECT c.url
        FROM downloads_url_chains AS c
        WHERE c.id = d.id
        ORDER BY c.chain_index ASC
        LIMIT 1
    ) AS source_url
FROM downloads AS d
ORDER BY d.start_time DESC
"""

_COOKIES_SQL = """
SELECT
    host_key AS host_key,
    name AS name,
    creation_utc AS creation_utc,
    last_access_utc AS last_access_utc,
    expires_utc AS expires_utc,
    is_secure AS is_secure,
    is_httponly AS is_httponly
FROM cookies
"""


def extract_chromium_history(
    history_path: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> list[BrowserVisit]:
    """Extract browsing history visits from a Chromium History database."""
    visits: list[BrowserVisit] = []
    with open_readonly_copy(history_path) as conn:
        if table_exists(conn, "visits") and table_exists(conn, "urls"):
            rows = fetch_all(conn, _HISTORY_VISITS_SQL)
        elif table_exists(conn, "urls"):
            rows = fetch_all(conn, _HISTORY_URLS_FALLBACK_SQL)
        else:
            logger.warning("No history tables found in '%s'", history_path.name)
            return []

        for row in rows:
            url = row["url"]
            engine, query = detect_search(url)
            transition = row["transition"]
            transition_name = None
            if transition is not None:
                transition_name = CHROMIUM_TRANSITION_NAMES.get(
                    int(transition) & 0xFF,
                    str(int(transition) & 0xFF),
                )
            visits.append(
                BrowserVisit(
                    browser=browser,
                    profile_name=profile_name,
                    url=url,
                    title=row["title"],
                    visit_count=row["visit_count"],
                    visit_time=chrome_timestamp_to_datetime(row["visit_time"]),
                    transition_type=transition_name,
                    search_engine=engine,
                    search_query=query,
                    domain=extract_domain(url),
                )
            )
    logger.info("Extracted %d Chrome/Edge history records from '%s'", len(visits), history_path.name)
    return visits


def extract_chromium_downloads(
    history_path: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> list[BrowserDownload]:
    """Extract downloads from a Chromium History database."""
    downloads: list[BrowserDownload] = []
    with open_readonly_copy(history_path) as conn:
        if not table_exists(conn, "downloads"):
            return []
        rows = fetch_all(conn, _DOWNLOADS_SQL)
        for row in rows:
            danger = row["danger_type"]
            danger_status = None
            if danger is not None:
                danger_status = CHROMIUM_DANGER_TYPES.get(int(danger), str(danger))
            size = row["total_bytes"]
            if size is None or int(size) < 0:
                size = row["received_bytes"]
            downloads.append(
                BrowserDownload(
                    browser=browser,
                    profile_name=profile_name,
                    source_url=row["source_url"],
                    local_path=row["target_path"] or row["current_path"],
                    downloaded_time=chrome_timestamp_to_datetime(row["start_time"]),
                    file_size=int(size) if size is not None else None,
                    danger_status=danger_status,
                )
            )
    logger.info(
        "Extracted %d Chrome/Edge download records from '%s'",
        len(downloads),
        history_path.name,
    )
    return downloads


def extract_chromium_cookies(
    cookies_path: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> list[BrowserCookieMetadata]:
    """Extract cookie metadata (never values) from a Chromium Cookies DB."""
    cookies: list[BrowserCookieMetadata] = []
    with open_readonly_copy(cookies_path) as conn:
        if not table_exists(conn, "cookies"):
            return []
        # Explicit column list excludes value / encrypted_value.
        rows = fetch_all(conn, _COOKIES_SQL)
        for row in rows:
            cookies.append(
                BrowserCookieMetadata(
                    browser=browser,
                    profile_name=profile_name,
                    host=row["host_key"],
                    name=row["name"],
                    creation_time=chrome_timestamp_to_datetime(row["creation_utc"]),
                    last_access_time=chrome_timestamp_to_datetime(row["last_access_utc"]),
                    expiration_time=chrome_timestamp_to_datetime(row["expires_utc"]),
                    secure=bool(row["is_secure"]) if row["is_secure"] is not None else None,
                    http_only=bool(row["is_httponly"]) if row["is_httponly"] is not None else None,
                )
            )
    logger.info(
        "Extracted %d Chrome/Edge cookie metadata records from '%s'",
        len(cookies),
        cookies_path.name,
    )
    return cookies


def extract_chromium_bookmarks(
    bookmarks_path: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> list[BrowserBookmark]:
    """Extract bookmarks from a Chromium Bookmarks JSON file."""
    try:
        payload = json.loads(bookmarks_path.read_text(encoding="utf-8"))
    except PermissionError as exc:
        raise EvidenceFileError(
            f"Permission denied reading bookmarks: {bookmarks_path}"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise BrowserHistoryError(
            f"Failed to parse bookmarks JSON '{bookmarks_path}': {exc}"
        ) from exc

    bookmarks: list[BrowserBookmark] = []
    roots = payload.get("roots", {})
    for root_name, node in roots.items():
        if isinstance(node, dict):
            _walk_bookmark_node(
                node,
                folder=node.get("name") or root_name,
                browser=browser,
                profile_name=profile_name,
                output=bookmarks,
            )
    logger.info(
        "Extracted %d Chrome/Edge bookmarks from '%s'",
        len(bookmarks),
        bookmarks_path.name,
    )
    return bookmarks


def _walk_bookmark_node(
    node: dict,
    *,
    folder: str,
    browser: str,
    profile_name: str | None,
    output: list[BrowserBookmark],
) -> None:
    """Recursively collect bookmark URLs from a Chromium bookmark node."""
    node_type = node.get("type")
    if node_type == "url":
        date_added = node.get("date_added")
        created = None
        if date_added is not None:
            try:
                created = chrome_timestamp_to_datetime(int(date_added))
            except (TypeError, ValueError):
                created = None
        output.append(
            BrowserBookmark(
                browser=browser,
                profile_name=profile_name,
                title=node.get("name"),
                url=node.get("url"),
                created_time=created,
                folder=folder,
            )
        )
        return

    children = node.get("children") or []
    current_folder = node.get("name") or folder
    for child in children:
        if isinstance(child, dict):
            next_folder = current_folder
            if child.get("type") == "folder":
                next_folder = child.get("name") or current_folder
            _walk_bookmark_node(
                child,
                folder=next_folder,
                browser=browser,
                profile_name=profile_name,
                output=output,
            )


def derive_searches(visits: list[BrowserVisit]) -> list[BrowserSearch]:
    """Build search-query records from history visits."""
    searches: list[BrowserSearch] = []
    for visit in visits:
        if visit.search_engine and visit.search_query:
            searches.append(
                BrowserSearch(
                    browser=visit.browser,
                    profile_name=visit.profile_name,
                    engine=visit.search_engine,
                    search_query=visit.search_query,
                    visit_time=visit.visit_time,
                    url=visit.url,
                )
            )
    return searches


def derive_login_pages(visits: list[BrowserVisit]) -> list[BrowserLoginPage]:
    """Build login-page records from history visits."""
    pages: list[BrowserLoginPage] = []
    for visit in visits:
        if is_login_page(visit.url):
            pages.append(
                BrowserLoginPage(
                    browser=visit.browser,
                    profile_name=visit.profile_name,
                    url=visit.url,
                    visit_time=visit.visit_time,
                    title=visit.title,
                )
            )
    return pages


def analyze_chrome_profile(
    profile_dir: Path,
    profile_name: str | None = None,
) -> BrowserArtifacts:
    """Analyze a Chrome profile directory and return artifact collections."""
    return analyze_chromium_profile(
        profile_dir,
        browser=BrowserType.CHROME.value,
        profile_name=profile_name or profile_dir.name,
    )


def analyze_chromium_profile(
    profile_dir: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> BrowserArtifacts:
    """Shared Chromium profile analysis used by Chrome and Edge.

    Args:
        profile_dir: Path to a Chromium-based profile folder.
        browser: Browser label (``Chrome`` or ``Edge``).
        profile_name: Optional profile label.

    Returns:
        Typed ``BrowserArtifacts`` collection.
    """
    if not profile_dir.is_dir():
        raise EvidenceFileError(f"Browser profile directory not found: {profile_dir}")

    history_path = profile_dir / "History"
    cookies_path = profile_dir / "Cookies"
    bookmarks_path = profile_dir / "Bookmarks"

    history: list[BrowserVisit] = []
    downloads: list[BrowserDownload] = []
    cookies: list[BrowserCookieMetadata] = []
    bookmarks: list[BrowserBookmark] = []

    if history_path.is_file():
        history = extract_chromium_history(
            history_path, browser=browser, profile_name=profile_name
        )
        downloads = extract_chromium_downloads(
            history_path, browser=browser, profile_name=profile_name
        )
    else:
        logger.warning("History database missing in profile '%s'", profile_dir)

    if cookies_path.is_file():
        cookies = extract_chromium_cookies(
            cookies_path, browser=browser, profile_name=profile_name
        )
    else:
        logger.warning("Cookies database missing in profile '%s'", profile_dir)

    if bookmarks_path.is_file():
        bookmarks = extract_chromium_bookmarks(
            bookmarks_path, browser=browser, profile_name=profile_name
        )
    else:
        logger.warning("Bookmarks file missing in profile '%s'", profile_dir)

    return BrowserArtifacts(
        browser=browser,
        profile_name=profile_name,
        history=history,
        downloads=downloads,
        bookmarks=bookmarks,
        cookies=cookies,
        searches=derive_searches(history),
        login_pages=derive_login_pages(history),
    )
