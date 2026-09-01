"""Phase 15 — dashboard, reports list, analysis history (read-only product APIs)."""

from __future__ import annotations

import pytest

from investigations.models import AnalysisRun, CustodyEventRecord, ReportRecord
from tests.test_integration_api import _upload

pytestmark = pytest.mark.django_db


def test_dashboard_summary_live_and_readonly(inv_client, case) -> None:
    upload = _upload(inv_client, case)
    assert upload.status_code == 201
    eid = upload.data["data"]["id"]

    custody_before = CustodyEventRecord.objects.filter(evidence_id=eid).count()
    analysis_before = AnalysisRun.objects.filter(evidence_id=eid).count()

    resp = inv_client.get("/api/dashboard/")
    assert resp.status_code == 200
    assert resp.data["success"] is True
    data = resp.data["data"]

    assert data["total_cases"] >= 1
    assert data["total_evidence"] >= 1
    assert "open_cases" in data
    assert "closed_cases" in data
    assert "reports_generated" in data
    assert isinstance(data["recent_cases"], list)
    assert isinstance(data["recent_evidence"], list)
    assert isinstance(data["recent_analysis"], list)
    assert isinstance(data["recent_custody"], list)
    assert isinstance(data["recent_reports"], list)
    assert "priority_counts" in data

    # Read-only: no new custody or analysis from dashboard load.
    assert CustodyEventRecord.objects.filter(evidence_id=eid).count() == custody_before
    assert AnalysisRun.objects.filter(evidence_id=eid).count() == analysis_before

    blob = str(data)
    assert "stored_path" not in blob
    assert "json_path" not in blob
    assert "pdf_path" not in blob


def test_reports_list_readonly_and_download(inv_client, case) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]

    empty = inv_client.get("/api/reports/")
    assert empty.status_code == 200
    assert empty.data["success"] is True
    assert empty.data["data"] == []

    generated = inv_client.post(
        f"/api/evidence/{eid}/report/", {"format": "json"}, format="json"
    )
    assert generated.status_code == 201
    report_db_id = generated.data["data"]["id"]

    listed = inv_client.get("/api/reports/")
    assert listed.status_code == 200
    rows = listed.data["data"]
    assert len(rows) >= 1
    row = next(r for r in rows if str(r["id"]) == str(report_db_id))
    assert row["report_id"]
    assert row["has_json"] is True
    assert "json_path" not in row
    assert "pdf_path" not in row
    assert row.get("case_title")
    assert row.get("evidence_filename")

    custody_before = CustodyEventRecord.objects.filter(evidence_id=eid).count()
    analysis_before = AnalysisRun.objects.filter(evidence_id=eid).count()
    latest_before = (
        CustodyEventRecord.objects.filter(evidence_id=eid)
        .order_by("-timestamp", "-created_at")
        .first()
    )
    chain_before = latest_before.event_hash if latest_before else None
    # Listing reports must not create custody events.
    listed_again = inv_client.get("/api/reports/")
    assert listed_again.status_code == 200
    assert CustodyEventRecord.objects.filter(evidence_id=eid).count() == custody_before

    download = inv_client.get(f"/api/reports/{report_db_id}/download/?format=json")
    assert download.status_code == 200
    assert download.get("Content-Disposition")
    # GET download is read-only: no custody, analysis, or hash-chain writes.
    assert CustodyEventRecord.objects.filter(evidence_id=eid).count() == custody_before
    assert AnalysisRun.objects.filter(evidence_id=eid).count() == analysis_before
    latest_after = (
        CustodyEventRecord.objects.filter(evidence_id=eid)
        .order_by("-timestamp", "-created_at")
        .first()
    )
    assert (latest_after.event_hash if latest_after else None) == chain_before


def test_analysis_history_readonly(inv_client, case) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]

    before = inv_client.get(f"/api/evidence/{eid}/analysis-runs/")
    assert before.status_code == 200
    assert before.data["success"] is True
    initial = before.data["data"]

    custody_before = CustodyEventRecord.objects.filter(evidence_id=eid).count()

    keywords = inv_client.post(
        f"/api/evidence/{eid}/keywords/",
        {"keywords": ["bitcoin"]},
        format="json",
    )
    assert keywords.status_code == 200

    history = inv_client.get(f"/api/evidence/{eid}/analysis-runs/")
    assert history.status_code == 200
    rows = history.data["data"]
    assert len(rows) >= len(initial) + 1
    keyword_rows = [r for r in rows if r["analysis_type"] == "keyword"]
    assert keyword_rows
    assert "result_summary" in keyword_rows[0]
    assert "stored_path" not in str(rows)

    # History GET must not add custody.
    assert CustodyEventRecord.objects.filter(evidence_id=eid).count() == (
        custody_before + 1
    )  # keyword analysis creates one event

    history_again = inv_client.get(f"/api/evidence/{eid}/analysis-runs/")
    assert history_again.status_code == 200
    assert CustodyEventRecord.objects.filter(evidence_id=eid).count() == (
        custody_before + 1
    )


def test_dashboard_requires_auth(api_client) -> None:
    resp = api_client.get("/api/dashboard/")
    assert resp.status_code in {401, 403}


def test_reports_list_requires_auth(api_client) -> None:
    resp = api_client.get("/api/reports/")
    assert resp.status_code in {401, 403}


def test_custody_list_readonly(inv_client, case) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]
    custody_before = CustodyEventRecord.objects.filter(evidence_id=eid).count()

    listed = inv_client.get("/api/custody/")
    assert listed.status_code == 200
    assert listed.data["success"] is True
    rows = listed.data["data"]
    assert isinstance(rows, list)
    assert len(rows) >= 1
    row = next(r for r in rows if str(r.get("evidence")) == str(eid))
    assert row["action"]
    assert row["timestamp"]
    assert "stored_path" not in str(rows)

    listed_again = inv_client.get("/api/custody/")
    assert listed_again.status_code == 200
    assert CustodyEventRecord.objects.filter(evidence_id=eid).count() == custody_before

    scoped = inv_client.get(f"/api/custody/?case_id={case.id}")
    assert scoped.status_code == 200
    assert all(str(r["case"]) == str(case.id) for r in scoped.data["data"])


def test_custody_list_requires_auth(api_client) -> None:
    resp = api_client.get("/api/custody/")
    assert resp.status_code in {401, 403}
