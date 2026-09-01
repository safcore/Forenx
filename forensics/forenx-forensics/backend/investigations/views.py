"""API views: thin JWT-protected wrappers around ForenX services."""

from __future__ import annotations

from django.http import FileResponse
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from investigations.api_errors import ApiError, success_payload
from investigations.models import Case, Evidence, ReportRecord
from investigations.permissions import (
    CanAccessCaseObject,
    CanManageCases,
    CanMutateEvidence,
    CanRunAnalysis,
    IsAuthenticatedAndActive,
    user_can_access_case,
)
from investigations.serializers import (
    AIAnalysisSerializer,
    CaseSerializer,
    EvidenceHashCompareSerializer,
    EvidenceSerializer,
    EvidenceUploadSerializer,
    KeywordAnalysisSerializer,
    ReportCreateSerializer,
    ReportSerializer,
)
from investigations import services


def _get_case_or_404(case_id, user) -> Case:
    try:
        case = Case.objects.get(id=case_id)
    except Case.DoesNotExist as exc:
        raise ApiError("CASE_NOT_FOUND", "Case was not found.", http_status=404) from exc
    if not user_can_access_case(user, case):
        raise ApiError(
            "PERMISSION_DENIED",
            "You do not have access to this case.",
            http_status=403,
        )
    return case


def _get_evidence_or_404(evidence_id, user) -> Evidence:
    try:
        evidence = Evidence.objects.select_related("case").get(id=evidence_id)
    except Evidence.DoesNotExist as exc:
        raise ApiError(
            "EVIDENCE_NOT_FOUND",
            "Evidence record was not found.",
            http_status=404,
        ) from exc
    if not user_can_access_case(user, evidence.case):
        raise ApiError(
            "PERMISSION_DENIED",
            "You do not have access to this evidence.",
            http_status=403,
        )
    return evidence


class CaseListCreateView(generics.ListCreateAPIView):
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticatedAndActive, CanManageCases]

    def get_queryset(self):
        user = self.request.user
        from accounts.models import UserRole

        qs = Case.objects.all().prefetch_related("members")
        if user.role in {UserRole.ADMINISTRATOR, UserRole.LEAD_INVESTIGATOR}:
            return qs
        return qs.filter(
            models_q_user(user)
        ).distinct()

    def perform_create(self, serializer):
        case = serializer.save(
            created_by=self.request.user,
            investigator=serializer.validated_data.get("investigator")
            or self.request.user,
        )
        case.members.add(self.request.user)


def models_q_user(user):
    from django.db.models import Q

    return Q(investigator=user) | Q(created_by=user) | Q(members=user)


class CaseDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticatedAndActive, CanAccessCaseObject]
    queryset = Case.objects.all()
    lookup_field = "id"


class EvidenceCollectionView(APIView):
    """GET list / POST upload for case evidence."""

    permission_classes = [IsAuthenticatedAndActive, CanMutateEvidence]
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticatedAndActive()]
        return [IsAuthenticatedAndActive(), CanMutateEvidence()]

    def get(self, request, case_id):
        case = _get_case_or_404(case_id, request.user)
        qs = Evidence.objects.filter(case=case).select_related("case", "uploaded_by")
        return Response(success_payload(EvidenceSerializer(qs, many=True).data))

    def post(self, request, case_id):
        case = _get_case_or_404(case_id, request.user)
        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = services.acquire_evidence(
            case=case,
            request=request,
            uploaded_file=serializer.validated_data["file"],
        )
        return Response(success_payload(payload), status=status.HTTP_201_CREATED)


class EvidenceDetailView(generics.RetrieveAPIView):
    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticatedAndActive]
    lookup_field = "id"

    def get_object(self):
        return _get_evidence_or_404(self.kwargs["id"], self.request.user)


class EvidenceHashView(APIView):
    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.run_hash_analysis(evidence=evidence, request=request)
        return Response(success_payload(data))


class EvidenceVerifyHashView(APIView):
    """Compare a reference digest against stored acquisition hashes (read-only)."""

    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        serializer = EvidenceHashCompareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = services.compare_acquisition_hash(
            evidence=evidence,
            algorithm=serializer.validated_data["algorithm"],
            expected_hash=serializer.validated_data["expected_hash"],
        )
        return Response(success_payload(data))


class EvidenceVerifyIntegrityView(APIView):
    """Recalculate digests from stored file and compare to acquisition hashes."""

    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.verify_evidence_integrity(
            evidence=evidence,
            request=request,
        )
        return Response(success_payload(data))


class EvidenceMetadataView(APIView):
    """GET /api/evidence/<uuid>/metadata/ — read-only latest stored metadata analysis."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.get_stored_analysis_result(evidence, "metadata")
        return Response(success_payload(data))


class EvidenceMetadataAnalyzeView(APIView):
    """POST /api/evidence/<uuid>/metadata/analyze/ — explicit metadata analysis."""

    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.run_metadata_analysis(evidence=evidence, request=request)
        return Response(success_payload(data))


class EvidenceKeywordView(APIView):
    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        serializer = KeywordAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = services.run_keyword_analysis(
            evidence=evidence,
            request=request,
            keywords=serializer.validated_data["keywords"],
        )
        return Response(success_payload(data))


class EvidenceBrowserView(APIView):
    """GET /api/evidence/<uuid>/browser/ — read-only latest stored browser analysis."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.get_stored_analysis_result(evidence, "browser")
        return Response(success_payload(data))


class EvidenceBrowserAnalyzeView(APIView):
    """POST /api/evidence/<uuid>/browser/analyze/ — explicit browser analysis."""

    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.run_browser_analysis(evidence=evidence, request=request)
        return Response(success_payload(data))


class EvidenceTimelineView(APIView):
    """GET /api/evidence/<uuid>/timeline/ — read-only latest stored timeline analysis."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.get_stored_analysis_result(evidence, "timeline")
        return Response(success_payload(data))


class EvidenceTimelineAnalyzeView(APIView):
    """POST /api/evidence/<uuid>/timeline/analyze/ — explicit timeline analysis."""

    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.run_timeline_analysis(evidence=evidence, request=request)
        return Response(success_payload(data))


class EvidenceCustodyView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.get_custody_chain(evidence=evidence, request=request)
        return Response(success_payload(data))


class EvidenceCustodyVerifyView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.verify_custody_chain(evidence=evidence, request=request)
        return Response(success_payload(data))


class EvidenceReportView(APIView):
    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        serializer = ReportCreateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = services.generate_report(
            evidence=evidence,
            request=request,
            output_format=serializer.validated_data.get("format", "json"),
        )
        return Response(success_payload(data), status=status.HTTP_201_CREATED)


class EvidenceAIView(APIView):
    """POST /api/evidence/<uuid>/ai/ and /ai-assist/ — advisory AI analysis."""

    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        serializer = AIAnalysisSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = services.run_ai_analysis(
            evidence=evidence,
            request=request,
            enabled=serializer.validated_data.get("enabled"),
            question=serializer.validated_data.get("question"),
        )
        return Response(success_payload(data))


class CaseReportCreateView(APIView):
    """POST /api/cases/<case_id>/reports/ — generate using first/latest evidence id body."""

    permission_classes = [IsAuthenticatedAndActive, CanRunAnalysis]

    def post(self, request, case_id):
        case = _get_case_or_404(case_id, request.user)
        evidence_id = request.data.get("evidence_id")
        if not evidence_id:
            raise ApiError("EVIDENCE_REQUIRED", "evidence_id is required.")
        evidence = _get_evidence_or_404(evidence_id, request.user)
        if evidence.case_id != case.id:
            raise ApiError(
                "EVIDENCE_CASE_MISMATCH",
                "Evidence does not belong to the specified case.",
                http_status=400,
            )
        serializer = ReportCreateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = services.generate_report(
            evidence=evidence,
            request=request,
            output_format=serializer.validated_data.get("format", "json"),
        )
        return Response(success_payload(data), status=status.HTTP_201_CREATED)


class DashboardSummaryView(APIView):
    """GET /api/dashboard/ — read-only aggregates for the investigator dashboard."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        data = services.get_dashboard_summary(request.user)
        return Response(success_payload(data))


class ReportListView(APIView):
    """GET /api/reports/ — list generated reports for accessible cases (read-only)."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        data = services.list_reports_for_user(request.user)
        return Response(success_payload(data))


class CustodyListView(APIView):
    """GET /api/custody/ — recent custody events for accessible cases (read-only)."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        case_id = request.query_params.get("case_id") or None
        if case_id:
            _get_case_or_404(case_id, request.user)
        data = services.list_custody_for_user(request.user, case_id=case_id)
        return Response(success_payload(data))


class EvidenceListView(APIView):
    """GET /api/evidence/ — inventory of accessible evidence (read-only)."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        case_id = request.query_params.get("case_id") or None
        if case_id:
            _get_case_or_404(case_id, request.user)
        data = services.list_evidence_for_user(request.user, case_id=case_id)
        return Response(success_payload(data))


class EvidenceAnalysisHistoryView(APIView):
    """GET /api/evidence/<uuid>/analysis-runs/ — read-only AnalysisRun history."""

    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, id):
        evidence = _get_evidence_or_404(id, request.user)
        data = services.list_analysis_runs_for_evidence(evidence)
        return Response(success_payload(data))


class ReportDetailView(generics.RetrieveAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticatedAndActive]
    lookup_field = "id"

    def get_object(self):
        try:
            report = ReportRecord.objects.select_related("case", "evidence").get(
                id=self.kwargs["id"]
            )
        except ReportRecord.DoesNotExist as exc:
            raise ApiError(
                "REPORT_NOT_FOUND", "Report was not found.", http_status=404
            ) from exc
        if not user_can_access_case(self.request.user, report.case):
            raise ApiError(
                "PERMISSION_DENIED",
                "You do not have access to this report.",
                http_status=403,
            )
        return report


class ReportDownloadView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request, id):
        try:
            report = ReportRecord.objects.select_related("case").get(id=id)
        except ReportRecord.DoesNotExist as exc:
            raise ApiError(
                "REPORT_NOT_FOUND", "Report was not found.", http_status=404
            ) from exc
        if not user_can_access_case(request.user, report.case):
            raise ApiError(
                "PERMISSION_DENIED",
                "You do not have access to this report.",
                http_status=403,
            )
        prefer = request.query_params.get("format", "json").lower()
        if prefer not in {"json", "pdf"}:
            prefer = "json"
        path = services.safe_report_download_path(report, prefer=prefer)
        return FileResponse(
            path.open("rb"),
            as_attachment=True,
            filename=path.name,
        )
