"""Phase 16 — analytics aggregates, global evidence inventory (read-only)."""

from __future__ import annotations

import pytest

from investigations.models import (
    AnalysisRun,
    AnalysisType,
    CustodyEventRecord,
    Evidence,
    ReportRecord,
)
from tests.conftest import auth_client
from tests.test_integration_api import _upload

pytestmark = pytest.mark.django_db


def _snapshot(eid):
    evidence = Evidence.objects.get(id=eid)
    return {
        "md5": evidence.md5,
        "sha1": evidence.sha1,
        "sha256": evidence.sha256,
        "metadata": evidence.metadata,
        "filename": evidence.original_filename,
        "file_size": evidence.file_size,
        "acquired_at": evidence.acquisition_timestamp,
        "evidence": Evidence.objects.count(),
        "analysis": AnalysisRun.objects.count(),
        "custody": CustodyEventRecord.objects.count(),
        "reports": ReportRecord.objects.count(),
    }


def test_dashboard_analytics_aggregates_and_readonly(inv_client, case) -> None:
    upload = _upload(inv_client, case)
    assert upload.status_code == 201
    eid = upload.data["data"]["id"]
    before = _snapshot(eid)

    resp = inv_client.get("/api/dashboard/")
    assert resp.status_code == 200
    data = resp.data["data"]

    assert data["total_cases"] >= 1
    assert data["total_evidence"] >= 1
    assert data["total_analysis_runs"] == before["analysis"]
    assert data["total_custody_events"] == before["custody"]
    assert isinstance(data["analysis_counts"], dict)
    for key in (
        AnalysisType.HASH,
        AnalysisType.KEYWORD,
        AnalysisType.BROWSER,
        AnalysisType.TIMELINE,
        AnalysisType.METADATA,
        AnalysisType.REPORT,
        AnalysisType.AI,
    ):
        assert key in data["analysis_counts"]
        assert isinstance(data["analysis_counts"][key], int)
    assert isinstance(data["custody_counts"], dict)
    assert isinstance(data["evidence_type_counts"], dict)
    assert isinstance(data.get("recent_timeline"), list)

    assert _snapshot(eid) == before
    blob = str(data)
    assert "stored_path" not in blob
    assert "json_path" not in blob


def test_dashboard_analytics_requires_auth(api_client) -> None:
    resp = api_client.get("/api/dashboard/")
    assert resp.status_code in {401, 403}


def test_global_evidence_list_readonly_and_scoped(
    inv_client, case, outsider
) -> None:
    upload = _upload(inv_client, case)
    assert upload.status_code == 201
    eid = upload.data["data"]["id"]
    before = _snapshot(eid)

    listed = inv_client.get("/api/evidence/")
    assert listed.status_code == 200
    assert listed.data["success"] is True
    rows = listed.data["data"]
    assert isinstance(rows, list)
    assert any(str(row["id"]) == str(eid) for row in rows)
    row = next(r for r in rows if str(r["id"]) == str(eid))
    assert row["original_filename"]
    assert row.get("case_title")
    assert "stored_path" not in row
    assert "json_path" not in row

    assert _snapshot(eid) == before

    listed_again = inv_client.get("/api/evidence/")
    assert listed_again.status_code == 200
    assert _snapshot(eid) == before

    other = auth_client(outsider)
    outsider_list = other.get("/api/evidence/")
    assert outsider_list.status_code == 200
    outsider_ids = {str(r["id"]) for r in outsider_list.data["data"]}
    assert str(eid) not in outsider_ids


def test_global_evidence_case_filter_enforces_access(
    inv_client, case, outsider
) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]

    scoped = inv_client.get(f"/api/evidence/?case_id={case.id}")
    assert scoped.status_code == 200
    assert all(str(r["case_id"]) == str(case.id) for r in scoped.data["data"])
    assert any(str(r["id"]) == str(eid) for r in scoped.data["data"])

    other = auth_client(outsider)
    denied = other.get(f"/api/evidence/?case_id={case.id}")
    assert denied.status_code == 403


def test_global_evidence_requires_auth(api_client) -> None:
    resp = api_client.get("/api/evidence/")
    assert resp.status_code in {401, 403}


def test_timeline_overview_from_dashboard_is_readonly(inv_client, case) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]
    before = _snapshot(eid)

    resp = inv_client.get("/api/dashboard/")
    assert resp.status_code == 200
    data = resp.data["data"]
    assert isinstance(data["recent_timeline"], list)
    for run in data["recent_timeline"]:
        assert run["analysis_type"] == AnalysisType.TIMELINE

    assert _snapshot(eid) == before
