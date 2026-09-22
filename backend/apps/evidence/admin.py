from django.contrib import admin

from .models import AnalysisRun, CustodyEventRecord, Evidence, ReportRecord


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_filename",
        "case",
        "file_size",
        "sha256",
        "uploaded_by",
        "acquisition_timestamp",
    )
    list_filter = ("case", "file_type", "created_at")
    search_fields = ("original_filename", "sha256", "md5")
    readonly_fields = (
        "id",
        "storage_name",
        "stored_path",
        "file_size",
        "md5",
        "sha1",
        "sha256",
        "metadata",
        "acquisition_timestamp",
        "created_at",
        "updated_at",
    )


@admin.register(CustodyEventRecord)
class CustodyEventRecordAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "action",
        "evidence",
        "actor_id",
        "timestamp",
        "event_hash",
    )
    list_filter = ("action", "source", "timestamp")
    search_fields = ("event_id", "description", "event_hash", "evidence_sha256")
    readonly_fields = [f.name for f in CustodyEventRecord._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "evidence",
        "analysis_type",
        "status",
        "created_by",
        "started_at",
        "completed_at",
    )
    list_filter = ("analysis_type", "status", "created_at")
    search_fields = ("evidence__original_filename", "error_message")
    readonly_fields = [f.name for f in AnalysisRun._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReportRecord)
class ReportRecordAdmin(admin.ModelAdmin):
    list_display = (
        "report_id",
        "title",
        "report_type",
        "evidence",
        "generated_by",
        "created_at",
    )
    list_filter = ("report_type", "created_at")
    search_fields = ("report_id", "title", "evidence__original_filename")
    readonly_fields = [f.name for f in ReportRecord._meta.fields]
