"""Internal browser analysis models and shared utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from urllib.parse import parse_qs, unquote_plus, urlparse

# Chromium transition type lower bits (chrome/browser/browser_transition_types.h)
CHROMIUM_TRANSITION_NAMES: dict[int, str] = {
    0: "link",
    1: "typed",
    2: "auto_bookmark",
    3: "auto_subframe",
    4: "manual_subframe",
    5: "generated",
    6: "auto_toplevel",
    7: "form_submit",
    8: "reload",
    9: "keyword",
    10: "keyword_generated",
}

CHROMIUM_DANGER_TYPES: dict[int, str] = {
    0: "not_dangerous",
    1: "dangerous_file",
    2: "dangerous_url",
    3: "dangerous_content",
    4: "maybe_dangerous_content",
    5: "uncommon_content",
    6: "user_validated",
    7: "dangerous_host",
    8: "potentially_unwanted",
    9: "allowlisted_by_policy",
    10: "async_scanning",
    11: "blocked",
    12: "password_protected",
    13: "blocked_too_large",
    14: "sensitive_content_warning",
    15: "sensitive_content_block",
    16: "deep_scanned_safe",
    17: "deep_scanned_opened_dangerous",
    18: "prompt_for_scanning",
}

_SEARCH_ENGINE_HOSTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "www.google.com": ("Google", ("q",)),
    "google.com": ("Google", ("q",)),
    "www.bing.com": ("Bing", ("q",)),
    "bing.com": ("Bing", ("q",)),
    "duckduckgo.com": ("DuckDuckGo", ("q",)),
    "www.duckduckgo.com": ("DuckDuckGo", ("q",)),
    "search.yahoo.com": ("Yahoo", ("p", "q")),
    "yahoo.com": ("Yahoo", ("p", "q")),
    "search.brave.com": ("Brave", ("q",)),
    "brave.com": ("Brave", ("q",)),
}

_LOGIN_MARKERS = (
    "login",
    "signin",
    "sign-in",
    "sign_in",
    "auth",
    "oauth",
    "account/login",
    "accounts/login",
    "accounts.google",
    "session/login",
)


class BrowserType(str, Enum):
    """Supported offline browser profile types."""

    CHROME = "Chrome"
    EDGE = "Edge"
    FIREFOX = "Firefox"


def chrome_timestamp_to_datetime(value: int | None) -> datetime | None:
    """Convert a Chromium timestamp to an aware UTC datetime.

    Chromium stores timestamps as microseconds since 1601-01-01 UTC.
    """
    if value is None or value <= 0:
        return None
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    try:
        return epoch + timedelta(microseconds=int(value))
    except (OverflowError, ValueError, OSError):
        return None


def firefox_timestamp_to_datetime(value: int | None) -> datetime | None:
    """Convert a Firefox PRTime timestamp to an aware UTC datetime.

    Firefox stores timestamps as microseconds since the UNIX epoch.
    """
    if value is None or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1_000_000, tz=timezone.utc)
    except (OverflowError, ValueError, OSError):
        return None


def extract_domain(url: str | None) -> str | None:
    """Extract the hostname/domain from a URL."""
    if not url:
        return None
    try:
        host = urlparse(url).hostname
    except ValueError:
        return None
    return host.lower() if host else None


def detect_search(url: str | None) -> tuple[str | None, str | None]:
    """Detect search engine and query string from a URL.

    Returns:
        Tuple of ``(engine_name, query)``; either may be ``None``.
    """
    if not url:
        return None, None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None, None

    host = (parsed.hostname or "").lower()
    bare = host[4:] if host.startswith("www.") else host

    engine_info = _SEARCH_ENGINE_HOSTS.get(host) or _SEARCH_ENGINE_HOSTS.get(bare)
    if engine_info is None:
        for known_host, info in _SEARCH_ENGINE_HOSTS.items():
            if host.endswith(known_host) or bare.endswith(known_host):
                engine_info = info
                break
    if engine_info is None:
        return None, None

    engine, params = engine_info
    query_map = parse_qs(parsed.query)
    for key in params:
        values = query_map.get(key)
        if values and values[0].strip():
            return engine, unquote_plus(values[0].strip())
    return engine, None


def is_login_page(url: str | None) -> bool:
    """Return whether a URL likely represents a login/auth page."""
    if not url:
        return False
    lowered = url.lower()
    return any(marker in lowered for marker in _LOGIN_MARKERS)
