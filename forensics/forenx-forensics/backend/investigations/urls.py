"""Investigation API routes."""

from django.urls import path

from investigations import views

urlpatterns = [
    path("dashboard/", views.DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("reports/", views.ReportListView.as_view(), name="report-list"),
    path("custody/", views.CustodyListView.as_view(), name="custody-list"),
    path("evidence/", views.EvidenceListView.as_view(), name="evidence-list"),
    path("cases/", views.CaseListCreateView.as_view(), name="case-list"),
    path("cases/<uuid:id>/", views.CaseDetailView.as_view(), name="case-detail"),
    path(
        "cases/<uuid:case_id>/evidence/",
        views.EvidenceCollectionView.as_view(),
        name="case-evidence",
    ),
    path(
        "cases/<uuid:case_id>/reports/",
        views.CaseReportCreateView.as_view(),
        name="case-report-create",
    ),
    path("evidence/<uuid:id>/", views.EvidenceDetailView.as_view(), name="evidence-detail"),
    path("evidence/<uuid:id>/hash/", views.EvidenceHashView.as_view(), name="evidence-hash"),
    path(
        "evidence/<uuid:id>/verify-hash/",
        views.EvidenceVerifyHashView.as_view(),
        name="evidence-verify-hash",
    ),
    path(
        "evidence/<uuid:id>/verify-integrity/",
        views.EvidenceVerifyIntegrityView.as_view(),
        name="evidence-verify-integrity",
    ),
    path(
        "evidence/<uuid:id>/metadata/analyze/",
        views.EvidenceMetadataAnalyzeView.as_view(),
        name="evidence-metadata-analyze",
    ),
    path(
        "evidence/<uuid:id>/metadata/",
        views.EvidenceMetadataView.as_view(),
        name="evidence-metadata",
    ),
    path(
        "evidence/<uuid:id>/keywords/",
        views.EvidenceKeywordView.as_view(),
        name="evidence-keywords",
    ),
    path(
        "evidence/<uuid:id>/browser/analyze/",
        views.EvidenceBrowserAnalyzeView.as_view(),
        name="evidence-browser-analyze",
    ),
    path(
        "evidence/<uuid:id>/browser/",
        views.EvidenceBrowserView.as_view(),
        name="evidence-browser",
    ),
    path(
        "evidence/<uuid:id>/timeline/analyze/",
        views.EvidenceTimelineAnalyzeView.as_view(),
        name="evidence-timeline-analyze",
    ),
    path(
        "evidence/<uuid:id>/timeline/",
        views.EvidenceTimelineView.as_view(),
        name="evidence-timeline",
    ),
    path(
        "evidence/<uuid:id>/custody/",
        views.EvidenceCustodyView.as_view(),
        name="evidence-custody",
    ),
    path(
        "evidence/<uuid:id>/custody/verify/",
        views.EvidenceCustodyVerifyView.as_view(),
        name="evidence-custody-verify",
    ),
    path(
        "evidence/<uuid:id>/report/",
        views.EvidenceReportView.as_view(),
        name="evidence-report",
    ),
    path("evidence/<uuid:id>/ai/", views.EvidenceAIView.as_view(), name="evidence-ai"),
    path(
        "evidence/<uuid:id>/ai-assist/",
        views.EvidenceAIView.as_view(),
        name="evidence-ai-assist",
    ),
    path(
        "evidence/<uuid:id>/analysis-runs/",
        views.EvidenceAnalysisHistoryView.as_view(),
        name="evidence-analysis-history",
    ),
    path("reports/<uuid:id>/", views.ReportDetailView.as_view(), name="report-detail"),
    path(
        "reports/<uuid:id>/download/",
        views.ReportDownloadView.as_view(),
        name="report-download",
    ),
]
