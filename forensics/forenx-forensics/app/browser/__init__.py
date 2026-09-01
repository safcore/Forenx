"""Browser artifact analysis package for the ForenX forensics engine."""

from app.browser.dispatcher import analyze_profile, detect_browser_type
from app.browser.models import BrowserType

__all__ = [
    "BrowserType",
    "analyze_profile",
    "detect_browser_type",
]
