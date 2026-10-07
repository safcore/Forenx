from django.urls import path

from .views import (
    CaseEvidenceCollectionView,
    CustodyListView,
    CustodyGlobalVerifyView,
    EvidenceAIView,
    EvidenceAnalysisHistoryView,
    EvidenceBrowserAnalyzeView,
    EvidenceBrowserView,
    EvidenceCustodyVerifyView,
    EvidenceCustodyView,
    EvidenceDetailView,
    EvidenceKeywordView,
    EvidenceListView,
    EvidenceMetadataAnalyzeView,
    EvidenceMetadataView,
    EvidenceReportView,
    EvidenceTimelineAnalyzeView,
    EvidenceTimelineView,
    EvidenceVerifyHashView,
    EvidenceVerifyIntegrityView,
    ReportDownloadView,
    ReportListView,
)

urlpatterns = [
    # Case-scoped evidence collection
    path("cases/<int:case_id>/evidence/", CaseEvidenceCollectionView.as_view(), name="case-evidence"),

    # Global evidence inventory & details
    path("evidence/", EvidenceListView.as_view(), name="evidence-list"),
    path("evidence/<uuid:id>/", EvidenceDetailView.as_view(), name="evidence-detail"),

    # Custody & integrity verification
    path("evidence/<uuid:id>/custody/", EvidenceCustodyView.as_view(), name="evidence-custody"),
    path("evidence/<uuid:id>/custody/verify/", EvidenceCustodyVerifyView.as_view(), name="evidence-custody-verify"),
    path("evidence/<uuid:id>/verify-hash/", EvidenceVerifyHashView.as_view(), name="evidence-verify-hash"),
    path("evidence/<uuid:id>/verify-integrity/", EvidenceVerifyIntegrityView.as_view(), name="evidence-verify-integrity"),
    path("custody/verify/", CustodyGlobalVerifyView.as_view(), name="custody-global-verify"),
    path("custody/", CustodyListView.as_view(), name="custody-list"),

    # Metadata analysis
    path("evidence/<uuid:id>/metadata/analyze/", EvidenceMetadataAnalyzeView.as_view(), name="evidence-metadata-analyze"),
    path("evidence/<uuid:id>/metadata/", EvidenceMetadataView.as_view(), name="evidence-metadata"),

    # Keyword search
    path("evidence/<uuid:id>/keywords/", EvidenceKeywordView.as_view(), name="evidence-keywords"),

    # Browser artifact analysis
    path("evidence/<uuid:id>/browser/analyze/", EvidenceBrowserAnalyzeView.as_view(), name="evidence-browser-analyze"),
    path("evidence/<uuid:id>/browser/", EvidenceBrowserView.as_view(), name="evidence-browser"),

    # Timeline reconstruction
    path("evidence/<uuid:id>/timeline/analyze/", EvidenceTimelineAnalyzeView.as_view(), name="evidence-timeline-analyze"),
    path("evidence/<uuid:id>/timeline/", EvidenceTimelineView.as_view(), name="evidence-timeline"),

    # Report generation and download
    path("evidence/<uuid:id>/report/", EvidenceReportView.as_view(), name="evidence-report"),
    path("reports/", ReportListView.as_view(), name="report-list"),
    path("reports/<uuid:id>/download/", ReportDownloadView.as_view(), name="report-download"),

    # Local AI assist
    path("evidence/<uuid:id>/ai-assist/", EvidenceAIView.as_view(), name="evidence-ai-assist"),

    # Analysis runs history
    path("evidence/<uuid:id>/analysis-runs/", EvidenceAnalysisHistoryView.as_view(), name="evidence-analysis-history"),
]
