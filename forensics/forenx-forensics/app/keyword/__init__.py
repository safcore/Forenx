"""Keyword search package for the ForenX forensics engine.

Public helpers:

- ``search_file`` / ``search_directory``
- ``detect_keyword_file_type``
- ``SearchOptions``
"""

from app.keyword.dispatcher import (
    KeywordFileType,
    detect_keyword_file_type,
    search_directory,
    search_file,
)
from app.keyword.search_engine import SearchOptions

__all__ = [
    "KeywordFileType",
    "SearchOptions",
    "detect_keyword_file_type",
    "search_file",
    "search_directory",
]
