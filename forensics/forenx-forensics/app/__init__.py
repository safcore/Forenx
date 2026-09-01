"""ForenX – AI-Assisted Digital Forensics Investigation Platform.

This package provides reusable forensic analysis modules intended for
standalone use or integration into a Django backend.
"""

from app.utils.config import PROJECT_VERSION

__version__ = PROJECT_VERSION
__all__ = ["__version__"]
