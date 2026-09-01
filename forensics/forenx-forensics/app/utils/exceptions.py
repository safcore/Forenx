"""Custom exception hierarchy for the ForenX forensics engine.

All domain-specific errors inherit from ``ForenXError`` so callers can
catch a single base type when integrating with Django or other fronts.
"""


class ForenXError(Exception):
    """Base exception for all ForenX forensic engine errors."""


class UnsupportedFileTypeError(ForenXError):
    """Raised when a file type is not supported by the current module."""


class HashVerificationError(ForenXError):
    """Raised when a computed hash does not match the expected value."""


class EvidenceFileError(ForenXError):
    """Raised when an evidence file path is missing, empty, or inaccessible."""


class UnsupportedAlgorithmError(ForenXError):
    """Raised when a requested hash algorithm is not supported."""


class InvalidHashError(ForenXError):
    """Raised when a provided hash digest is empty or malformed."""


class MetadataExtractionError(ForenXError):
    """Raised when metadata cannot be extracted from an evidence file."""


class BrowserHistoryError(ForenXError):
    """Raised when browser history or artifact parsing fails."""


class KeywordSearchError(ForenXError):
    """Raised when a keyword search operation fails."""


class TimelineError(ForenXError):
    """Raised when timeline construction or event processing fails."""


class CustodyError(ForenXError):
    """Raised when chain-of-custody recording or verification fails."""


class ReportError(ForenXError):
    """Raised when forensic report validation or generation fails."""


class ReportGenerationError(ReportError):
    """Backward-compatible alias for report generation failures."""


class AIAnalysisError(ForenXError):
    """Raised when AI-assisted analysis validation or orchestration fails."""
