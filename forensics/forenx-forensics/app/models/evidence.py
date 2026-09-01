"""Evidence data model for the ForenX forensics engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class Evidence:
    """Represents a single piece of digital forensic evidence.

    This model is intentionally framework-agnostic so it can be reused
    from CLI tools, tests, or a Django persistence layer.

    Attributes:
        evidence_id: Unique identifier for this evidence item.
        file_name: Original filename of the evidence file.
        file_path: Absolute or relative path to the evidence on disk.
        file_size: Size of the file in bytes.
        mime_type: MIME type of the file (e.g. ``image/jpeg``).
        uploaded_at: UTC timestamp when the evidence was registered.
            Defaults to the current UTC time if not supplied.
    """

    evidence_id: str
    file_name: str
    file_path: Path
    file_size: int
    mime_type: str
    uploaded_at: datetime | None = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        """Normalize ``file_path`` to a ``Path`` instance."""
        if not isinstance(self.file_path, Path):
            self.file_path = Path(self.file_path)
