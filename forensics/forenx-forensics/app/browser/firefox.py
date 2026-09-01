"""Mozilla Firefox offline profile artifact extraction."""

from __future__ import annotations

from pathlib import Path

from app.browser.chrome import derive_login_pages, derive_searches
from app.browser.models import (
    BrowserType,
    detect_search,
    extract_domain,
    firefox_timestamp_to_datetime,
)
from app.browser.sqlite_reader import fetch_all, open_readonly_copy, table_exists
from app.schemas.browser import (
    BrowserArtifacts,
    BrowserBookmark,
    BrowserCookieMetadata,
    BrowserDownload,
    BrowserVisit,
)
from app.utils.exceptions import EvidenceFileError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_FIREFOX_HISTORY_SQL = """
SELECT
    p.url AS url,
    p.title AS title,
    p.visit_count AS visit_count,
    h.visit_date AS visit_time,
    h.visit_type AS visit_type
FROM moz_historyvisits AS h
JOIN moz_places AS p ON p.id = h.place_id
ORDER BY h.visit_date DESC
"""

_FIREFOX_HISTORY_FALLBACK_SQL = """
SELECT
    url AS url,
    title AS title,
    visit_count AS visit_count,
    last_visit_date AS visit_time,
    NULL AS visit_type
FROM moz_places
WHERE url IS NOT NULL
ORDER BY last_visit_date DESC
"""

_FIREFOX_BOOKMARKS_SQL = """
SELECT
    b.title AS title,
    p.url AS url,
    b.dateAdded AS date_added,
    f.title AS folder
FROM moz_bookmarks AS b
LEFT JOIN moz_places AS p ON p.id = b.fk
LEFT JOIN moz_bookmarks AS f ON f.id = b.parent
WHERE b.type = 1
  AND p.url IS NOT NULL
ORDER BY b.dateAdded DESC
"""

_FIREFOX_DOWNLOADS_SQL = """
SELECT
    p.url AS source_url,
    a.content AS local_path,
    a.dateAdded AS downloaded_time
FROM moz_annos AS a
JOIN moz_places AS p ON p.id = a.place_id
JOIN moz_anno_attributes AS attr ON attr.id = a.anno_attribute_id
WHERE attr.name = 'downloads/destinationFileURI'
   OR attr.name = 'downloads/destinationFileName'
ORDER BY a.dateAdded DESC
"""

_FIREFOX_COOKIES_SQL = """
SELECT
    host AS host,
    name AS name,
    creationTime AS creation_time,
    lastAccessed AS last_access_time,
    expiry AS expiry,
    isSecure AS is_secure,
    isHttpOnly AS is_http_only
FROM moz_cookies
"""

_FIREFOX_VISIT_TYPES: dict[int, str] = {
    1: "link",
    2: "typed",
    3: "bookmark",
    4: "embed",
    5: "redirect_permanent",
    6: "redirect_temporary",
    7: "download",
    8: "framed_link",
    9: "reload",
}


def extract_firefox_history(
    places_path: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> list[BrowserVisit]:
    """Extract browsing history from Firefox ``places.sqlite``."""
    visits: list[BrowserVisit] = []
    with open_readonly_copy(places_path) as conn:
        if table_exists(conn, "moz_historyvisits") and table_exists(conn, "moz_places"):
            rows = fetch_all(conn, _FIREFOX_HISTORY_SQL)
        elif table_exists(conn, "moz_places"):
            rows = fetch_all(conn, _FIREFOX_HISTORY_FALLBACK_SQL)
        else:
            return []

        for row in rows:
            url = row["url"]
            engine, query = detect_search(url)
            visit_type = row["visit_type"]
            transition = None
            if visit_type is not None:
                transition = _FIREFOX_VISIT_TYPES.get(int(visit_type), str(visit_type))
            visits.append(
                BrowserVisit(
                    browser=browser,
                    profile_name=profile_name,
                    url=url,
                    title=row["title"],
                    visit_count=row["visit_count"],
                    visit_time=firefox_timestamp_to_datetime(row["visit_time"]),
                    transition_type=transition,
                    search_engine=engine,
                    search_query=query,
                    domain=extract_domain(url),
                )
            )
    logger.info("Extracted %d Firefox history records from '%s'", len(visits), places_path.name)
    return visits


def extract_firefox_bookmarks(
    places_path: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> list[BrowserBookmark]:
    """Extract bookmarks from Firefox ``places.sqlite``."""
    bookmarks: list[BrowserBookmark] = []
    with open_readonly_copy(places_path) as conn:
        if not table_exists(conn, "moz_bookmarks"):
            return []
        rows = fetch_all(conn, _FIREFOX_BOOKMARKS_SQL)
        for row in rows:
            bookmarks.append(
                BrowserBookmark(
                    browser=browser,
                    profile_name=profile_name,
                    title=row["title"],
                    url=row["url"],
                    created_time=firefox_timestamp_to_datetime(row["date_added"]),
                    folder=row["folder"],
                )
            )
    logger.info(
        "Extracted %d Firefox bookmarks from '%s'",
        len(bookmarks),
        places_path.name,
    )
    return bookmarks


def extract_firefox_downloads(
    places_path: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> list[BrowserDownload]:
    """Extract download annotations from Firefox ``places.sqlite``."""
    downloads: list[BrowserDownload] = []
    with open_readonly_copy(places_path) as conn:
        if not (
            table_exists(conn, "moz_annos")
            and table_exists(conn, "moz_anno_attributes")
            and table_exists(conn, "moz_places")
        ):
            return []
        try:
            rows = fetch_all(conn, _FIREFOX_DOWNLOADS_SQL)
        except Exception:  # noqa: BLE001 - optional annotation tables may differ
            logger.warning("Firefox downloads annotations unavailable in '%s'", places_path.name)
            return []

        for row in rows:
            local_path = row["local_path"]
            if isinstance(local_path, str) and local_path.startswith("file:"):
                # Convert file URIs to native paths without hardcoded drive letters.
                from urllib.parse import unquote, urlparse
                from urllib.request import url2pathname

                parsed = urlparse(local_path)
                local_path = url2pathname(unquote(parsed.path))
            downloads.append(
                BrowserDownload(
                    browser=browser,
                    profile_name=profile_name,
                    source_url=row["source_url"],
                    local_path=local_path,
                    downloaded_time=firefox_timestamp_to_datetime(row["downloaded_time"]),
                    file_size=None,
                    danger_status=None,
                )
            )
    logger.info(
        "Extracted %d Firefox download records from '%s'",
        len(downloads),
        places_path.name,
    )
    return downloads


def extract_firefox_cookies(
    cookies_path: Path,
    *,
    browser: str,
    profile_name: str | None,
) -> list[BrowserCookieMetadata]:
    """Extract cookie metadata (never values) from Firefox ``cookies.sqlite``."""
    cookies: list[BrowserCookieMetadata] = []
    with open_readonly_copy(cookies_path) as conn:
        if not table_exists(conn, "moz_cookies"):
            return []
        rows = fetch_all(conn, _FIREFOX_COOKIES_SQL)
        for row in rows:
            expiry = row["expiry"]
            expiration = None
            if expiry is not None:
                # Firefox expiry is seconds since UNIX epoch.
                try:
                    from datetime import datetime, timezone

                    expiration = datetime.fromtimestamp(int(expiry), tz=timezone.utc)
                except (OverflowError, ValueError, OSError):
                    expiration = None
            cookies.append(
                BrowserCookieMetadata(
                    browser=browser,
                    profile_name=profile_name,
                    host=row["host"],
                    name=row["name"],
                    creation_time=firefox_timestamp_to_datetime(row["creation_time"]),
                    last_access_time=firefox_timestamp_to_datetime(row["last_access_time"]),
                    expiration_time=expiration,
                    secure=bool(row["is_secure"]) if row["is_secure"] is not None else None,
                    http_only=bool(row["is_http_only"]) if row["is_http_only"] is not None else None,
                )
            )
    logger.info(
        "Extracted %d Firefox cookie metadata records from '%s'",
        len(cookies),
        cookies_path.name,
    )
    return cookies


def analyze_firefox_profile(
    profile_dir: Path,
    profile_name: str | None = None,
) -> BrowserArtifacts:
    """Analyze a Firefox profile directory and return artifact collections."""
    if not profile_dir.is_dir():
        raise EvidenceFileError(f"Browser profile directory not found: {profile_dir}")

    browser = BrowserType.FIREFOX.value
    profile_label = profile_name or profile_dir.name
    places_path = profile_dir / "places.sqlite"
    cookies_path = profile_dir / "cookies.sqlite"

    history: list[BrowserVisit] = []
    downloads: list[BrowserDownload] = []
    bookmarks: list[BrowserBookmark] = []
    cookies: list[BrowserCookieMetadata] = []

    if places_path.is_file():
        history = extract_firefox_history(
            places_path, browser=browser, profile_name=profile_label
        )
        bookmarks = extract_firefox_bookmarks(
            places_path, browser=browser, profile_name=profile_label
        )
        downloads = extract_firefox_downloads(
            places_path, browser=browser, profile_name=profile_label
        )
    else:
        logger.warning("places.sqlite missing in Firefox profile '%s'", profile_dir)

    if cookies_path.is_file():
        cookies = extract_firefox_cookies(
            cookies_path, browser=browser, profile_name=profile_label
        )
    else:
        logger.warning("cookies.sqlite missing in Firefox profile '%s'", profile_dir)

    return BrowserArtifacts(
        browser=browser,
        profile_name=profile_label,
        history=history,
        downloads=downloads,
        bookmarks=bookmarks,
        cookies=cookies,
        searches=derive_searches(history),
        login_pages=derive_login_pages(history),
    )
