"""Django admin for investigation models."""

from django.contrib import admin

from investigations.models import (
    AnalysisRun,
    Case,
    CustodyEventRecord,
    Evidence,
    ReportRecord,
)


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "investigator", "created_at")
    filter_horizontal = ("members",)


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "case", "sha256", "file_size", "created_at")
    readonly_fields = ("md5", "sha1", "sha256", "stored_path", "storage_name")


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ("analysis_type", "status", "evidence", "created_at")


@admin.register(CustodyEventRecord)
class CustodyEventRecordAdmin(admin.ModelAdmin):
    list_display = ("event_id", "action", "evidence", "timestamp")
    readonly_fields = ("event_hash", "previous_event_hash")


@admin.register(ReportRecord)
class ReportRecordAdmin(admin.ModelAdmin):
    list_display = ("report_id", "report_type", "case", "created_at")
