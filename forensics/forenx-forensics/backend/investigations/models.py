"""Persistence models for cases, evidence, analysis, custody, and reports.

These models store host-owned records. Forensic computation remains in ForenX.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class CaseStatus(models.TextChoices):
    OPEN = "open", "Open"
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"
    ARCHIVED = "archived", "Archived"


class CasePriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class AnalysisType(models.TextChoices):
    HASH = "hash", "Hash"
    METADATA = "metadata", "Metadata"
    KEYWORD = "keyword", "Keyword"
    BROWSER = "browser", "Browser"
    TIMELINE = "timeline", "Timeline"
    CUSTODY = "custody", "Custody"
    REPORT = "report", "Report"
    AI = "ai", "AI"


class AnalysisStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class Case(models.Model):
    """Investigation case."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="investigated_cases",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="case_memberships",
        blank=True,
    )
    priority = models.CharField(
        max_length=16,
        choices=CasePriority.choices,
        default=CasePriority.MEDIUM,
    )
    status = models.CharField(
        max_length=16,
        choices=CaseStatus.choices,
        default=CaseStatus.OPEN,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_cases",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Evidence(models.Model):
    """Acquired evidence artifact with integrity digests."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="evidence")
    original_filename = models.CharField(max_length=512)
    storage_name = models.CharField(max_length=128, unique=True)
    stored_path = models.CharField(max_length=1024)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=128, blank=True, default="")
    mime_type = models.CharField(max_length=128, blank=True, default="")
    md5 = models.CharField(max_length=32, blank=True, default="")
    sha1 = models.CharField(max_length=40, blank=True, default="")
    sha256 = models.CharField(max_length=64, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    acquisition_timestamp = models.DateTimeField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_evidence",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "evidence"

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.id})"


class AnalysisRun(models.Model):
    """Persisted analysis execution against an evidence item."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="analysis_runs")
    evidence = models.ForeignKey(
        Evidence, on_delete=models.CASCADE, related_name="analysis_runs"
    )
    analysis_type = models.CharField(max_length=32, choices=AnalysisType.choices)
    status = models.CharField(
        max_length=16,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="analysis_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class CustodyEventRecord(models.Model):
    """Persisted custody event fields produced by ForenX CustodyService."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="custody_events")
    evidence = models.ForeignKey(
        Evidence, on_delete=models.CASCADE, related_name="custody_events"
    )
    event_id = models.CharField(max_length=64, unique=True)
    action = models.CharField(max_length=64)
    actor_id = models.CharField(max_length=128, blank=True, default="")
    actor_role = models.CharField(max_length=64, blank=True, default="")
    source = models.CharField(max_length=64, blank=True, default="django")
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField()
    description = models.TextField()
    evidence_sha256 = models.CharField(max_length=64, blank=True, default="")
    previous_event_hash = models.CharField(max_length=64, null=True, blank=True)
    event_hash = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp", "created_at"]
        indexes = [
            models.Index(fields=["evidence", "timestamp"]),
        ]


class ReportRecord(models.Model):
    """Persisted metadata for a generated forensic report."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="reports")
    evidence = models.ForeignKey(
        Evidence, on_delete=models.CASCADE, related_name="reports"
    )
    report_id = models.CharField(max_length=64, unique=True)
    report_type = models.CharField(max_length=16, default="json")
    title = models.CharField(max_length=255, blank=True, default="")
    json_path = models.CharField(max_length=1024, blank=True, default="")
    pdf_path = models.CharField(max_length=1024, blank=True, default="")
    summary = models.JSONField(default=dict, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="generated_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
