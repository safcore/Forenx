"""Synthetic browser profile builders for Phase 5 samples and tests."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def chrome_time(dt: datetime) -> int:
    """Convert datetime to Chromium microsecond timestamp."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return int((dt - epoch).total_seconds() * 1_000_000)


def firefox_time(dt: datetime) -> int:
    """Convert datetime to Firefox PRTime microseconds."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000)


def build_chromium_profile(profile_dir: Path, *, rich: bool = True) -> Path:
    """Create a synthetic Chromium profile with History/Cookies/Bookmarks."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    now = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)

    history_path = profile_dir / "History"
    if history_path.exists():
        history_path.unlink()
    conn = sqlite3.connect(history_path)
    try:
        conn.executescript(
            """
            CREATE TABLE urls (
                id INTEGER PRIMARY KEY,
                url TEXT,
                title TEXT,
                visit_count INTEGER,
                typed_count INTEGER DEFAULT 0,
                last_visit_time INTEGER,
                hidden INTEGER DEFAULT 0
            );
            CREATE TABLE visits (
                id INTEGER PRIMARY KEY,
                url INTEGER,
                visit_time INTEGER,
                from_visit INTEGER DEFAULT 0,
                transition INTEGER DEFAULT 0,
                segment_id INTEGER DEFAULT 0,
                visit_duration INTEGER DEFAULT 0
            );
            CREATE TABLE downloads (
                id INTEGER PRIMARY KEY,
                guid TEXT,
                current_path TEXT,
                target_path TEXT,
                start_time INTEGER,
                received_bytes INTEGER,
                total_bytes INTEGER,
                state INTEGER,
                danger_type INTEGER,
                interrupt_reason INTEGER DEFAULT 0,
                hash BLOB,
                end_time INTEGER,
                opened INTEGER DEFAULT 0,
                last_access_time INTEGER,
                transient INTEGER DEFAULT 0,
                referrer TEXT,
                site_url TEXT,
                tab_url TEXT,
                tab_referrer_url TEXT,
                http_method TEXT,
                by_ext_id TEXT,
                by_ext_name TEXT,
                etag TEXT,
                last_modified TEXT,
                mime_type TEXT,
                original_mime_type TEXT
            );
            CREATE TABLE downloads_url_chains (
                id INTEGER,
                chain_index INTEGER,
                url TEXT,
                PRIMARY KEY (id, chain_index)
            );
            """
        )

        history_rows = [
            ("https://drive.google.com", "Google Drive", 4),
            ("https://www.dropbox.com", "Dropbox", 3),
            ("https://github.com", "GitHub", 6),
            ("https://accounts.google.com/signin", "Google Accounts", 2),
            ("https://login.microsoftonline.com/oauth", "Microsoft Login", 2),
            ("https://mail.google.com", "Gmail", 5),
            ("https://example.com", "Example Domain", 1),
            ("https://www.google.com/search?q=confidential+report", "confidential report - Google Search", 1),
            ("https://www.bing.com/search?q=bitcoin+wallet", "bitcoin wallet - Bing", 1),
            ("https://duckduckgo.com/?q=salary.xlsx", "salary.xlsx at DuckDuckGo", 1),
            ("https://search.yahoo.com/search?p=project+x", "project x - Yahoo Search", 1),
            ("https://search.brave.com/search?q=usb+recovery", "usb recovery - Brave Search", 1),
        ]
        if not rich:
            history_rows = history_rows[:3]

        for index, (url, title, count) in enumerate(history_rows, start=1):
            visit_time = chrome_time(now - timedelta(hours=index))
            conn.execute(
                "INSERT INTO urls(id, url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?, ?)",
                (index, url, title, count, visit_time),
            )
            conn.execute(
                "INSERT INTO visits(id, url, visit_time, transition) VALUES (?, ?, ?, ?)",
                (index, index, visit_time, 1 if index % 2 else 0),
            )

        downloads = [
            (
                1,
                "C:/Users/suspect/Downloads/salary.xlsx",
                "https://example.com/salary.xlsx",
                1024,
                0,
            ),
            (
                2,
                "C:/Users/suspect/Downloads/project_x.zip",
                "https://github.com/org/project-x/archive/main.zip",
                2048,
                5,
            ),
            (
                3,
                "C:/Users/suspect/Downloads/usb_recovery.pdf",
                "https://drive.google.com/uc?id=abc",
                4096,
                0,
            ),
        ]
        for download_id, target, source, size, danger in downloads:
            start = chrome_time(now - timedelta(days=download_id))
            conn.execute(
                """
                INSERT INTO downloads(
                    id, guid, current_path, target_path, start_time,
                    received_bytes, total_bytes, state, danger_type, end_time,
                    last_access_time, mime_type, original_mime_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, 'application/octet-stream', 'application/octet-stream')
                """,
                (
                    download_id,
                    f"guid-{download_id}",
                    target,
                    target,
                    start,
                    size,
                    size,
                    danger,
                    start,
                    start,
                ),
            )
            conn.execute(
                "INSERT INTO downloads_url_chains(id, chain_index, url) VALUES (?, 0, ?)",
                (download_id, source),
            )
        conn.commit()
    finally:
        conn.close()

    cookies_path = profile_dir / "Cookies"
    if cookies_path.exists():
        cookies_path.unlink()
    conn = sqlite3.connect(cookies_path)
    try:
        conn.execute(
            """
            CREATE TABLE cookies (
                creation_utc INTEGER NOT NULL,
                host_key TEXT NOT NULL,
                top_frame_site_key TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                encrypted_value BLOB DEFAULT '',
                path TEXT NOT NULL,
                expires_utc INTEGER NOT NULL,
                is_secure INTEGER NOT NULL,
                is_httponly INTEGER NOT NULL,
                last_access_utc INTEGER NOT NULL,
                has_expires INTEGER NOT NULL DEFAULT 1,
                is_persistent INTEGER NOT NULL DEFAULT 1,
                priority INTEGER NOT NULL DEFAULT 1,
                samesite INTEGER NOT NULL DEFAULT -1,
                source_scheme INTEGER NOT NULL DEFAULT 0,
                source_port INTEGER NOT NULL DEFAULT -1,
                is_same_party INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cookie_hosts = [
            ".google.com",
            ".dropbox.com",
            ".github.com",
            "mail.google.com",
            "example.com",
            ".microsoft.com",
        ]
        cookie_id = 0
        for host in cookie_hosts:
            for n in range(3):
                cookie_id += 1
                created = chrome_time(now - timedelta(days=cookie_id))
                conn.execute(
                    """
                    INSERT INTO cookies(
                        creation_utc, host_key, name, value, path,
                        expires_utc, is_secure, is_httponly, last_access_utc
                    ) VALUES (?, ?, ?, ?, '/', ?, ?, ?, ?)
                    """,
                    (
                        created,
                        host,
                        f"session_meta_{cookie_id}",
                        "REDACTED_SHOULD_NOT_BE_READ",
                        chrome_time(now + timedelta(days=30)),
                        1 if n % 2 == 0 else 0,
                        1 if n % 3 == 0 else 0,
                        created,
                    ),
                )
        conn.commit()
    finally:
        conn.close()

    bookmarks = {
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "type": "url",
                        "name": "Drive",
                        "url": "https://drive.google.com",
                        "date_added": str(chrome_time(now - timedelta(days=10))),
                    },
                    {
                        "type": "url",
                        "name": "Dropbox",
                        "url": "https://www.dropbox.com",
                        "date_added": str(chrome_time(now - timedelta(days=9))),
                    },
                    {
                        "type": "folder",
                        "name": "Work",
                        "children": [
                            {
                                "type": "url",
                                "name": "GitHub",
                                "url": "https://github.com",
                                "date_added": str(chrome_time(now - timedelta(days=8))),
                            },
                            {
                                "type": "url",
                                "name": "Gmail",
                                "url": "https://mail.google.com",
                                "date_added": str(chrome_time(now - timedelta(days=7))),
                            },
                            {
                                "type": "url",
                                "name": "Example",
                                "url": "https://example.com",
                                "date_added": str(chrome_time(now - timedelta(days=6))),
                            },
                        ],
                    },
                ],
                "name": "Bookmarks bar",
                "type": "folder",
            },
            "other": {"children": [], "name": "Other bookmarks", "type": "folder"},
            "synced": {"children": [], "name": "Mobile bookmarks", "type": "folder"},
        },
        "version": 1,
    }
    (profile_dir / "Bookmarks").write_text(json.dumps(bookmarks), encoding="utf-8")
    return profile_dir


def build_firefox_profile(profile_dir: Path) -> Path:
    """Create a synthetic Firefox profile with places.sqlite and cookies.sqlite."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    now = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)

    places = profile_dir / "places.sqlite"
    if places.exists():
        places.unlink()
    conn = sqlite3.connect(places)
    try:
        conn.executescript(
            """
            CREATE TABLE moz_places (
                id INTEGER PRIMARY KEY,
                url TEXT,
                title TEXT,
                visit_count INTEGER,
                last_visit_date INTEGER
            );
            CREATE TABLE moz_historyvisits (
                id INTEGER PRIMARY KEY,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER
            );
            CREATE TABLE moz_bookmarks (
                id INTEGER PRIMARY KEY,
                type INTEGER,
                fk INTEGER,
                parent INTEGER,
                title TEXT,
                dateAdded INTEGER
            );
            CREATE TABLE moz_anno_attributes (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
            CREATE TABLE moz_annos (
                id INTEGER PRIMARY KEY,
                place_id INTEGER,
                anno_attribute_id INTEGER,
                content TEXT,
                dateAdded INTEGER
            );
            """
        )
        rows = [
            ("https://drive.google.com", "Google Drive", 2),
            ("https://www.dropbox.com", "Dropbox", 1),
            ("https://github.com", "GitHub", 3),
            ("https://accounts.google.com/signin", "Google Sign-In", 1),
            ("https://www.google.com/search?q=confidential+report", "Search", 1),
            ("https://example.com", "Example", 1),
        ]
        for index, (url, title, count) in enumerate(rows, start=1):
            visit_time = firefox_time(now - timedelta(hours=index))
            conn.execute(
                "INSERT INTO moz_places(id, url, title, visit_count, last_visit_date) VALUES (?, ?, ?, ?, ?)",
                (index, url, title, count, visit_time),
            )
            conn.execute(
                "INSERT INTO moz_historyvisits(id, place_id, visit_date, visit_type) VALUES (?, ?, ?, ?)",
                (index, index, visit_time, 1),
            )

        conn.execute(
            "INSERT INTO moz_bookmarks(id, type, fk, parent, title, dateAdded) VALUES (1, 2, NULL, 0, 'toolbar', ?)",
            (firefox_time(now - timedelta(days=20)),),
        )
        conn.execute(
            "INSERT INTO moz_bookmarks(id, type, fk, parent, title, dateAdded) VALUES (2, 1, 3, 1, 'GitHub', ?)",
            (firefox_time(now - timedelta(days=5)),),
        )
        conn.execute(
            "INSERT INTO moz_anno_attributes(id, name) VALUES (1, 'downloads/destinationFileURI')"
        )
        conn.execute(
            """
            INSERT INTO moz_annos(id, place_id, anno_attribute_id, content, dateAdded)
            VALUES (1, 1, 1, 'file:///C:/Users/suspect/Downloads/report.pdf', ?)
            """,
            (firefox_time(now - timedelta(days=2)),),
        )
        conn.commit()
    finally:
        conn.close()

    cookies = profile_dir / "cookies.sqlite"
    if cookies.exists():
        cookies.unlink()
    conn = sqlite3.connect(cookies)
    try:
        conn.execute(
            """
            CREATE TABLE moz_cookies (
                id INTEGER PRIMARY KEY,
                originAttributes TEXT DEFAULT '',
                name TEXT,
                value TEXT,
                host TEXT,
                path TEXT,
                expiry INTEGER,
                lastAccessed INTEGER,
                creationTime INTEGER,
                isSecure INTEGER,
                isHttpOnly INTEGER
            )
            """
        )
        for index in range(1, 7):
            created = firefox_time(now - timedelta(days=index))
            conn.execute(
                """
                INSERT INTO moz_cookies(
                    id, name, value, host, path, expiry, lastAccessed, creationTime, isSecure, isHttpOnly
                ) VALUES (?, ?, 'REDACTED', ?, '/', ?, ?, ?, 1, 0)
                """,
                (
                    index,
                    f"ff_meta_{index}",
                    ".mozilla.org",
                    int((now + timedelta(days=30)).timestamp()),
                    created,
                    created,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return profile_dir
