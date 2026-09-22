from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cases.models import Case

from .models import CustodyEventRecord, Evidence, ReportRecord
from .serializers import (
    AIAssistRequestSerializer,
    CustodyEventSerializer,
    EvidenceSerializer,
    EvidenceUploadSerializer,
    HashVerifyRequestSerializer,
    KeywordSearchRequestSerializer,
    ReportCreateSerializer,
    ReportRecordSerializer,
)
from .services import (
    _schema_dump,
    acquire_evidence,
    generate_report,
    get_latest_browser_analysis,
    get_latest_metadata_analysis,
    get_latest_timeline_analysis,
    hydrate_custody_service,
    list_evidence_analysis_runs,
    run_ai_analysis,
    run_browser_analysis,
    run_keyword_analysis,
    run_metadata_analysis,
    run_timeline_analysis,
    safe_report_download_path,
    verify_evidence_hash,
    verify_evidence_integrity,
)


class CaseEvidenceCollectionView(APIView):
    """GET list and POST upload/acquisition for a specific case's evidence."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, case_id: int):
        case = get_object_or_404(Case, id=case_id, investigator=request.user)
        evidence_qs = (
            Evidence.objects.filter(case=case)
            .select_related("case", "uploaded_by")
            .order_by("-created_at")
        )
        serializer = EvidenceSerializer(evidence_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, case_id: int):
        case = get_object_or_404(Case, id=case_id, investigator=request.user)
        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = acquire_evidence(
            case=case,
            request=request,
            uploaded_file=serializer.validated_data["file"],
        )
        return Response(payload, status=status.HTTP_201_CREATED)


class EvidenceListView(generics.ListAPIView):
    """GET /api/evidence/ — list all evidence across accessible cases."""

    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Evidence.objects.filter(case__investigator=self.request.user)
            .select_related("case", "uploaded_by")
            .order_by("-created_at")
        )


class EvidenceDetailView(generics.RetrieveAPIView):
    """GET /api/evidence/<uuid:id>/ — single evidence details (paths redacted)."""

    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Evidence.objects.filter(
            case__investigator=self.request.user
        ).select_related("case", "uploaded_by")


class EvidenceCustodyView(APIView):
    """GET /api/evidence/<uuid:id>/custody/ — chain of custody history."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        events = evidence.custody_events.order_by("timestamp", "created_at")
        serializer = CustodyEventSerializer(events, many=True)
        return Response(
            {
                "evidence_id": str(evidence.id),
                "events": serializer.data,
                "count": len(serializer.data),
            },
            status=status.HTTP_200_OK,
        )


class EvidenceCustodyVerifyView(APIView):
    """GET /api/evidence/<uuid:id>/custody/verify/ — verify hash chain."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        service = hydrate_custody_service(evidence)
        verification = service.verify_chain(str(evidence.id))
        return Response(
            {"success": True, "data": _schema_dump(verification)},
            status=status.HTTP_200_OK,
        )


class EvidenceVerifyHashView(APIView):
    """POST /api/evidence/<uuid:id>/verify-hash/ — reference digest comparison."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        serializer = HashVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = verify_evidence_hash(
            evidence=evidence,
            algorithm=serializer.validated_data["algorithm"],
            expected_hash=serializer.validated_data["expected_hash"],
        )
        return Response(payload, status=status.HTTP_200_OK)


class EvidenceVerifyIntegrityView(APIView):
    """POST /api/evidence/<uuid:id>/verify-integrity/ — disk re-hash verification."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        payload = verify_evidence_integrity(evidence=evidence, request=request)
        return Response(payload, status=status.HTTP_200_OK)


class CustodyListView(APIView):
    """GET /api/custody/ — global custody events queryable by ?case_id=<id>."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        qs = CustodyEventRecord.objects.filter(case__investigator=request.user)
        if case_id:
            qs = qs.filter(case_id=case_id)
        qs = qs.select_related("case", "evidence").order_by("timestamp", "created_at")
        serializer = CustodyEventSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ============================================================================
# Forensic Analysis Views
# ============================================================================

class EvidenceMetadataAnalyzeView(APIView):
    """POST /api/evidence/<uuid:id>/metadata/analyze/ — execute metadata analysis."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        payload = run_metadata_analysis(evidence=evidence, request=request)
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_200_OK,
        )


class EvidenceMetadataView(APIView):
    """GET /api/evidence/<uuid:id>/metadata/ — get latest cached metadata result."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        payload = get_latest_metadata_analysis(evidence=evidence)
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_200_OK,
        )


class EvidenceKeywordView(APIView):
    """POST /api/evidence/<uuid:id>/keywords/ — keyword search."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        serializer = KeywordSearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = run_keyword_analysis(
            evidence=evidence,
            request=request,
            keywords=serializer.validated_data["keywords"],
            case_sensitive=serializer.validated_data.get("case_sensitive", False),
            whole_word=serializer.validated_data.get("whole_word", False),
            regex=serializer.validated_data.get("regex", False),
            context_chars=serializer.validated_data.get("context_chars", 20),
        )
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_200_OK,
        )


class EvidenceBrowserAnalyzeView(APIView):
    """POST /api/evidence/<uuid:id>/browser/analyze/ — execute browser analysis."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        payload = run_browser_analysis(evidence=evidence, request=request)
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_200_OK,
        )


class EvidenceBrowserView(APIView):
    """GET /api/evidence/<uuid:id>/browser/ — get latest cached browser result."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        payload = get_latest_browser_analysis(evidence=evidence)
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_200_OK,
        )


class EvidenceTimelineAnalyzeView(APIView):
    """POST /api/evidence/<uuid:id>/timeline/analyze/ — execute timeline analysis."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        payload = run_timeline_analysis(evidence=evidence, request=request)
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_200_OK,
        )


class EvidenceTimelineView(APIView):
    """GET /api/evidence/<uuid:id>/timeline/ — get latest cached timeline result."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        payload = get_latest_timeline_analysis(evidence=evidence)
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_200_OK,
        )


class EvidenceReportView(APIView):
    """POST /api/evidence/<uuid:id>/report/ — generate forensic report."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = generate_report(
            evidence=evidence,
            request=request,
            output_format=serializer.validated_data.get("format", "both"),
        )
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_201_CREATED,
        )


class ReportDownloadView(APIView):
    """GET /api/reports/<uuid:id>/download/?format=pdf|json — authenticated report download."""

    permission_classes = [IsAuthenticated]

    def perform_content_negotiation(self, request, force=False):
        """Bypass DRF format suffix negotiation so ?format=pdf/json serves file streams."""
        renderers = self.get_renderers()
        return (renderers[0], renderers[0].media_type)

    def get(self, request, id):
        record = get_object_or_404(
            ReportRecord, id=id, case__investigator=request.user
        )
        prefer = request.query_params.get("format", "pdf").lower()
        file_path = safe_report_download_path(record, prefer=prefer)

        content_type = "application/pdf" if prefer == "pdf" else "application/json"
        response = FileResponse(open(file_path, "rb"), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
        return response


class ReportListView(generics.ListAPIView):
    """GET /api/reports/ — list generated reports across accessible cases."""

    serializer_class = ReportRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ReportRecord.objects.filter(case__investigator=self.request.user)
            .select_related("case", "evidence", "generated_by")
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({"success": True, "data": response.data})


class EvidenceAIView(APIView):
    """POST /api/evidence/<uuid:id>/ai-assist/ — local offline AI assist."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        serializer = AIAssistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = run_ai_analysis(
            evidence=evidence,
            request=request,
            question=serializer.validated_data.get("question"),
        )
        return Response(
            {"success": True, "data": payload},
            status=status.HTTP_200_OK,
        )


class EvidenceAnalysisHistoryView(APIView):
    """GET /api/evidence/<uuid:id>/analysis-runs/ — read-only history of AnalysisRuns."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        evidence = get_object_or_404(
            Evidence, id=id, case__investigator=request.user
        )
        runs = list_evidence_analysis_runs(evidence=evidence)
        return Response(
            {"success": True, "data": runs},
            status=status.HTTP_200_OK,
        )
