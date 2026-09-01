"""Pydantic schemas for forensic investigation report generation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.ai import AIAnalysis


class ReportStatus(str, Enum):
    """Overall report generation status."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class FindingSeverity(str, Enum):
    """Neutral severity labels for structured findings."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NoteCategory(str, Enum):
    """Categories for investigator-supplied notes."""

    OBSERVATION = "OBSERVATION"
    FINDING = "FINDING"
    HYPOTHESIS = "HYPOTHESIS"
    LIMITATION = "LIMITATION"
    CONCLUSION = "CONCLUSION"


class ReportMetadata(BaseModel):
    """Identity and authorship metadata for a forensic report."""

    report_id: str
    case_id: str
    evidence_id: str
    title: str
    investigator: str | None = None
    generated_at: datetime
    timezone: str = "UTC"
    report_version: str = "1.0"
    generated_by: str = "ForenX ReportService"
    provenance: dict[str, Any] = Field(default_factory=dict)


class EvidenceSummary(BaseModel):
    """High-level evidence identity summary."""

    evidence_id: str
    case_id: str
    evidence_path: str | None = None
    original_filename: str | None = None
    evidence_type: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    mime_type: str | None = None
    evidence_sha256: str | None = None
    modules_executed: list[str] = Field(default_factory=list)


class HashReportSection(BaseModel):
    """Derived hash / integrity section (evidence hashes, not custody event hashes)."""

    available: bool = True
    evidence_path: str | None = None
    algorithms: dict[str, str] = Field(default_factory=dict)
    primary_sha256: str | None = None
    verification_verified: bool | None = None
    integrity_status: str | None = None
    integrity_verified: bool | None = None
    message: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class MetadataReportSection(BaseModel):
    """Derived metadata section from MetadataService output."""

    available: bool = True
    file_type: str | None = None
    filesystem: dict[str, Any] | None = None
    image: dict[str, Any] | None = None
    pdf: dict[str, Any] | None = None
    document: dict[str, Any] | None = None
    message: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class KeywordReportSection(BaseModel):
    """Derived keyword-search section from KeywordSearchService output."""

    available: bool = True
    searched_keywords: list[str] = Field(default_factory=list)
    total_files_searched: int = Field(default=0, ge=0)
    total_matches: int = Field(default=0, ge=0)
    files_with_matches: int = Field(default=0, ge=0)
    keyword_frequency: dict[str, int] = Field(default_factory=dict)
    matched_files: list[str] = Field(default_factory=list)
    matches: list[dict[str, Any]] = Field(default_factory=list)
    message: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class BrowserReportSection(BaseModel):
    """Derived browser-analysis section (cookie metadata only; never values)."""

    available: bool = True
    profiles: list[dict[str, Any]] = Field(default_factory=list)
    history_count: int = Field(default=0, ge=0)
    download_count: int = Field(default=0, ge=0)
    bookmark_count: int = Field(default=0, ge=0)
    search_count: int = Field(default=0, ge=0)
    login_page_count: int = Field(default=0, ge=0)
    cookie_metadata_count: int = Field(default=0, ge=0)
    message: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class TimelineReportSection(BaseModel):
    """Derived timeline section from TimelineService output."""

    available: bool = True
    total_events: int = Field(default=0, ge=0)
    events_by_type: dict[str, int] = Field(default_factory=dict)
    events_by_source: dict[str, int] = Field(default_factory=dict)
    earliest_event: datetime | None = None
    latest_event: datetime | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    timezone_policy: str = "UTC-normalized where source policy applies"
    message: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class CustodyReportSection(BaseModel):
    """Derived chain-of-custody section from CustodyService output."""

    available: bool = True
    event_count: int = Field(default=0, ge=0)
    events: list[dict[str, Any]] = Field(default_factory=list)
    chain_valid: bool | None = None
    verification_message: str | None = None
    broken_event_id: str | None = None
    first_event_id: str | None = None
    last_event_id: str | None = None
    message: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class InvestigationNote(BaseModel):
    """Manually supplied investigator note."""

    author: str
    timestamp: datetime
    note: str
    category: NoteCategory = NoteCategory.OBSERVATION


class InvestigationNotes(BaseModel):
    """Collection of investigator notes."""

    notes: list[InvestigationNote] = Field(default_factory=list)


class Finding(BaseModel):
    """Structured forensic finding expressed in neutral language."""

    finding_id: str
    title: str
    severity: FindingSeverity
    description: str
    evidence_reference: str | None = None
    source: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    timestamp: datetime | None = None


class ForensicReport(BaseModel):
    """Complete forensic investigation report (derived artifact)."""

    report_id: str
    case_id: str
    evidence_id: str
    title: str
    investigator: str | None = None
    generated_at: datetime
    timezone: str = "UTC"
    report_version: str = "1.0"
    generation_status: ReportStatus
    executive_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: EvidenceSummary
    hash_results: HashReportSection | None = None
    metadata_results: MetadataReportSection | None = None
    keyword_results: KeywordReportSection | None = None
    browser_results: BrowserReportSection | None = None
    timeline_results: TimelineReportSection | None = None
    custody_results: CustodyReportSection | None = None
    ai_analysis: AIAnalysis | None = None
    investigation_notes: InvestigationNotes = Field(default_factory=InvestigationNotes)
    findings: list[Finding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    conclusion: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    report_metadata: ReportMetadata | None = None


class ReportGenerationResult(BaseModel):
    """Outcome of writing a report to disk."""

    status: ReportStatus
    report_id: str
    case_id: str
    evidence_id: str
    output_format: str
    output_path: str | None = None
    message: str
    generated_at: datetime
    warnings: list[str] = Field(default_factory=list)
