"""Smoke tests for Phase 1 project scaffolding.

These tests verify structural foundations only. No forensic behavior is
exercised.
"""

from pathlib import Path

from app.models.evidence import Evidence
from app.utils.config import (
    ASSETS_DIRECTORY,
    BASE_DIR,
    LOG_DIRECTORY,
    OUTPUTS_DIRECTORY,
    PROJECT_NAME,
    PROJECT_VERSION,
    REQUIRED_DIRECTORIES,
    VERSION_FILE,
)


def test_version_file_exists() -> None:
    """VERSION file exists at the project root."""
    assert VERSION_FILE.is_file()


def test_project_identity_from_version_file() -> None:
    """Project version is loaded dynamically from VERSION."""
    assert PROJECT_NAME == "ForenX Forensics Engine"
    assert PROJECT_VERSION == VERSION_FILE.read_text(encoding="utf-8").strip()
    assert PROJECT_VERSION == "1.0.0"


def test_outputs_directory_exists_in_layout() -> None:
    """outputs/ path is configured and present under the project root."""
    assert OUTPUTS_DIRECTORY == BASE_DIR / "outputs"
    assert OUTPUTS_DIRECTORY.is_dir()
    assert OUTPUTS_DIRECTORY in REQUIRED_DIRECTORIES


def test_services_folder_exists() -> None:
    """app/services package exists."""
    services_dir = BASE_DIR / "app" / "services"
    assert services_dir.is_dir()
    assert (services_dir / "__init__.py").is_file()
    assert (services_dir / "README.md").is_file()


def test_schemas_folder_exists() -> None:
    """app/schemas package exists with placeholder modules."""
    schemas_dir = BASE_DIR / "app" / "schemas"
    assert schemas_dir.is_dir()
    assert (schemas_dir / "__init__.py").is_file()
    for name in ("hash.py", "metadata.py", "timeline.py", "report.py"):
        assert (schemas_dir / name).is_file()


def test_logs_folder_configured() -> None:
    """logs/ directory exists at the project root."""
    assert LOG_DIRECTORY == BASE_DIR / "logs"
    assert LOG_DIRECTORY.is_dir()
    assert LOG_DIRECTORY in REQUIRED_DIRECTORIES


def test_assets_folder_configured() -> None:
    """assets/ directory and subfolders exist in the project layout."""
    assert ASSETS_DIRECTORY == BASE_DIR / "assets"
    assert ASSETS_DIRECTORY.is_dir()
    assert (ASSETS_DIRECTORY / "logo").is_dir()
    assert (ASSETS_DIRECTORY / "icons").is_dir()
    assert (ASSETS_DIRECTORY / "report_templates").is_dir()
    assert ASSETS_DIRECTORY in REQUIRED_DIRECTORIES


def test_evidence_dataclass() -> None:
    """Evidence model accepts required fields and normalizes paths."""
    item = Evidence(
        evidence_id="ev-001",
        file_name="sample.jpg",
        file_path="evidence/images/sample.jpg",
        file_size=1024,
        mime_type="image/jpeg",
    )
    assert item.evidence_id == "ev-001"
    assert isinstance(item.file_path, Path)
    assert item.uploaded_at is not None


def test_required_directories_are_paths() -> None:
    """Required directory list is non-empty and uses pathlib Paths."""
    assert len(REQUIRED_DIRECTORIES) > 0
    assert all(isinstance(path, Path) for path in REQUIRED_DIRECTORIES)
