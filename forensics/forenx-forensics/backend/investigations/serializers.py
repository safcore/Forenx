"""DRF serializers for investigation resources."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from investigations.models import (
    AnalysisRun,
    Case,
    CustodyEventRecord,
    Evidence,
    ReportRecord,
)

User = get_user_model()


class CaseSerializer(serializers.ModelSerializer):
    investigator_username = serializers.CharField(
        source="investigator.username", read_only=True
    )
    member_ids = serializers.PrimaryKeyRelatedField(
        source="members",
        many=True,
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = Case
        fields = (
            "id",
            "title",
            "description",
            "investigator",
            "investigator_username",
            "member_ids",
            "priority",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")
        extra_kwargs = {
            # Optional on create — CaseListCreateView.perform_create defaults
            # to request.user when omitted.
            "investigator": {"required": False, "allow_null": False},
            "description": {"required": False, "allow_blank": True},
            "priority": {"required": False},
            "status": {"required": False},
        }


class EvidenceSerializer(serializers.ModelSerializer):
    """Evidence metadata without exposing raw filesystem internals by default."""

    storage_available = serializers.SerializerMethodField()
    case_title = serializers.CharField(source="case.title", read_only=True)

    class Meta:
        model = Evidence
        fields = (
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
        )
        read_only_fields = fields

    def get_storage_available(self, obj: Evidence) -> bool:
        from pathlib import Path

        return Path(obj.stored_path).is_file()


class EvidenceUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class EvidenceHashCompareSerializer(serializers.Serializer):
    algorithm = serializers.ChoiceField(choices=["md5", "sha1", "sha256"])
    expected_hash = serializers.CharField(max_length=128, trim_whitespace=True)


class KeywordAnalysisSerializer(serializers.Serializer):
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=128),
        allow_empty=False,
        max_length=50,
    )


class ReportCreateSerializer(serializers.Serializer):
    format = serializers.ChoiceField(
        choices=["json", "pdf", "both"],
        default="json",
        required=False,
    )


class AIAnalysisSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(required=False, default=None, allow_null=True)
    question = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )


class AnalysisRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisRun
        fields = (
            "id",
            "case",
            "evidence",
            "analysis_type",
            "status",
            "started_at",
            "completed_at",
            "result",
            "error_message",
            "created_by",
            "created_at",
        )
        read_only_fields = fields


class CustodyEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustodyEventRecord
        fields = (
            "id",
            "case",
            "evidence",
            "event_id",
            "action",
            "actor_id",
            "actor_role",
            "source",
            "source_ip",
            "timestamp",
            "description",
            "evidence_sha256",
            "previous_event_hash",
            "event_hash",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class ReportSerializer(serializers.ModelSerializer):
    has_json = serializers.SerializerMethodField()
    has_pdf = serializers.SerializerMethodField()
    case_title = serializers.CharField(source="case.title", read_only=True)
    evidence_filename = serializers.CharField(
        source="evidence.original_filename", read_only=True
    )
    generated_by_username = serializers.CharField(
        source="generated_by.username", read_only=True
    )

    class Meta:
        model = ReportRecord
        fields = (
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
            "summary",
            "generated_by",
            "generated_by_username",
            "created_at",
        )
        read_only_fields = fields

    def get_has_json(self, obj: ReportRecord) -> bool:
        return bool(obj.json_path)

    def get_has_pdf(self, obj: ReportRecord) -> bool:
        return bool(obj.pdf_path)
