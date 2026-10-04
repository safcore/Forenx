from pathlib import Path

from rest_framework import serializers

from .models import AnalysisRun, CustodyEventRecord, Evidence, ReportRecord


class EvidenceSerializer(serializers.ModelSerializer):
    case_id = serializers.CharField(source="case.id", read_only=True)
    case_title = serializers.CharField(source="case.title", read_only=True)
    uploaded_by = serializers.CharField(source="uploaded_by.username", read_only=True)
    storage_available = serializers.SerializerMethodField()

    class Meta:
        model = Evidence
        fields = [
            "id",
            "case_id",
            "case_title",
            "original_filename",
            "file_size",
            "file_type",
            "mime_type",
            "md5",
            "sha1",
            "sha256",
            "metadata",
            "acquisition_timestamp",
            "uploaded_by",
            "storage_available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_storage_available(self, obj) -> bool:
        """Check whether the evidence file exists locally or in Supabase Storage."""
        from .storage import is_storage_available

        return is_storage_available(obj)


class EvidenceUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)


class HashVerifyRequestSerializer(serializers.Serializer):
    algorithm = serializers.CharField(required=True)
    expected_hash = serializers.CharField(required=True)


class CustodyEventSerializer(serializers.ModelSerializer):
    evidence = serializers.CharField(source="evidence.id", read_only=True)
    evidence_filename = serializers.CharField(source="evidence.original_filename", read_only=True)
    case = serializers.CharField(source="case.id", read_only=True)
    case_title = serializers.CharField(source="case.title", read_only=True)

    class Meta:
        model = CustodyEventRecord
        fields = [
            "id",
            "event_id",
            "action",
            "actor_id",
            "actor_role",
            "source",
            "source_ip",
            "timestamp",
            "description",
            "evidence",
            "evidence_filename",
            "case",
            "case_title",
            "evidence_sha256",
            "previous_event_hash",
            "event_hash",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class KeywordSearchRequestSerializer(serializers.Serializer):
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=128),
        allow_empty=False,
        max_length=50,
        required=True,
    )
    case_sensitive = serializers.BooleanField(required=False, default=False)
    whole_word = serializers.BooleanField(required=False, default=False)
    regex = serializers.BooleanField(required=False, default=False)
    context_chars = serializers.IntegerField(
        required=False, default=20, min_value=5, max_value=200
    )


class ReportCreateSerializer(serializers.Serializer):
    format = serializers.ChoiceField(
        choices=["json", "pdf", "both"],
        required=False,
        default="both",
    )


class AIAssistRequestSerializer(serializers.Serializer):
    question = serializers.CharField(
        required=False, allow_blank=True, max_length=1000
    )
    enabled = serializers.BooleanField(required=False, default=True)


class AnalysisRunSerializer(serializers.ModelSerializer):
    case = serializers.CharField(source="case.id", read_only=True)
    evidence = serializers.CharField(source="evidence.id", read_only=True)
    created_by = serializers.CharField(source="created_by.id", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )
    result_summary = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisRun
        fields = [
            "id",
            "case",
            "evidence",
            "analysis_type",
            "status",
            "started_at",
            "completed_at",
            "created_at",
            "created_by",
            "created_by_username",
            "result_summary",
            "error_message",
        ]
        read_only_fields = fields

    def get_result_summary(self, obj) -> str:
        from .services import _analysis_run_result_summary

        return _analysis_run_result_summary(obj)

    def get_error_message(self, obj) -> str:
        from .services import _sanitize_error_message

        return _sanitize_error_message(obj.error_message)


class ReportRecordSerializer(serializers.ModelSerializer):
    case = serializers.CharField(source="case.id", read_only=True)
    evidence = serializers.CharField(source="evidence.id", read_only=True)
    case_title = serializers.CharField(source="case.title", read_only=True)
    evidence_filename = serializers.CharField(
        source="evidence.original_filename", read_only=True
    )
    has_json = serializers.SerializerMethodField()
    has_pdf = serializers.SerializerMethodField()
    generated_by = serializers.CharField(source="generated_by.id", read_only=True)
    generated_by_username = serializers.CharField(
        source="generated_by.username", read_only=True
    )

    class Meta:
        model = ReportRecord
        fields = [
            "id",
            "case",
            "evidence",
            "case_title",
            "evidence_filename",
            "report_id",
            "report_type",
            "title",
            "has_json",
            "has_pdf",
            "generated_by",
            "generated_by_username",
            "created_at",
        ]
        read_only_fields = fields

    def get_has_json(self, obj) -> bool:
        return bool(obj.json_path and Path(obj.json_path).is_file())

    def get_has_pdf(self, obj) -> bool:
        return bool(obj.pdf_path and Path(obj.pdf_path).is_file())
