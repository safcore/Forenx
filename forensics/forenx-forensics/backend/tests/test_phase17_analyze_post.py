"""Phase 17.2 — browser/timeline/metadata analysis uses explicit POST."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from investigations.models import AnalysisRun, CustodyEventRecord
from tests.conftest import auth_client
from tests.test_integration_api import _attach_browser_profile_evidence, _upload

pytestmark = pytest.mark.django_db


def _counts(eid):
    return (
        AnalysisRun.objects.filter(evidence_id=eid).count(),
        CustodyEventRecord.objects.filter(evidence_id=eid).count(),
    )


def test_get_browser_timeline_metadata_is_readonly(inv_client, case) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]
    analysis_before, custody_before = _counts(eid)

    for kind in ("browser", "timeline", "metadata"):
        resp = inv_client.get(f"/api/evidence/{eid}/{kind}/")
        assert resp.status_code == 200, kind
        assert resp.data["success"] is True
        assert resp.data["data"]["status"] == "not_performed"
        assert AnalysisRun.objects.filter(evidence_id=eid).count() == analysis_before
        assert (
            CustodyEventRecord.objects.filter(evidence_id=eid).count() == custody_before
        )


def test_post_timeline_analyze_runs_once_get_does_not(inv_client, case) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]
    analysis_before, custody_before = _counts(eid)

    viewed = inv_client.get(f"/api/evidence/{eid}/timeline/")
    assert viewed.status_code == 200
    assert viewed.data["data"]["status"] == "not_performed"
    assert _counts(eid) == (analysis_before, custody_before)

    ran = inv_client.post(f"/api/evidence/{eid}/timeline/analyze/")
    assert ran.status_code == 200
    assert ran.data["success"] is True
    assert ran.data["data"]["summary"]["total_events"] >= 1
    analysis_after, custody_after = _counts(eid)
    assert analysis_after == analysis_before + 1
    assert custody_after == custody_before + 1
    assert (
        AnalysisRun.objects.filter(evidence_id=eid, analysis_type="timeline").count()
        == 1
    )

    viewed_again = inv_client.get(f"/api/evidence/{eid}/timeline/")
    assert viewed_again.status_code == 200
    assert viewed_again.data["data"]["summary"]["total_events"] >= 1
    assert _counts(eid) == (analysis_after, custody_after)


def test_post_metadata_analyze_runs_once_get_does_not(inv_client, case) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]
    analysis_before, custody_before = _counts(eid)

    viewed = inv_client.get(f"/api/evidence/{eid}/metadata/")
    assert viewed.status_code == 200
    assert viewed.data["data"]["status"] == "not_performed"
    assert _counts(eid) == (analysis_before, custody_before)

    ran = inv_client.post(f"/api/evidence/{eid}/metadata/analyze/")
    assert ran.status_code == 200
    assert ran.data["data"]["file_type"] == "filesystem"
    analysis_after, custody_after = _counts(eid)
    assert analysis_after == analysis_before + 1
    assert custody_after == custody_before + 1
    assert (
        AnalysisRun.objects.filter(evidence_id=eid, analysis_type="metadata").count()
        == 1
    )

    viewed_again = inv_client.get(f"/api/evidence/{eid}/metadata/")
    assert viewed_again.status_code == 200
    assert viewed_again.data["data"]["file_type"] == "filesystem"
    assert _counts(eid) == (analysis_after, custody_after)


def test_post_browser_analyze_runs_once_get_does_not(
    inv_client, case, tmp_path
) -> None:
    evidence = _attach_browser_profile_evidence(inv_client, case, tmp_path)
    eid = evidence.id
    analysis_before, custody_before = _counts(eid)

    viewed = inv_client.get(f"/api/evidence/{eid}/browser/")
    assert viewed.status_code == 200
    assert viewed.data["data"]["status"] == "not_performed"
    assert _counts(eid) == (analysis_before, custody_before)

    ran = inv_client.post(f"/api/evidence/{eid}/browser/analyze/")
    assert ran.status_code == 200
    assert ran.data["data"]["browser"]
    analysis_after, custody_after = _counts(eid)
    assert analysis_after == analysis_before + 1
    assert custody_after == custody_before + 1
    assert (
        AnalysisRun.objects.filter(evidence_id=eid, analysis_type="browser").count() == 1
    )

    viewed_again = inv_client.get(f"/api/evidence/{eid}/browser/")
    assert viewed_again.status_code == 200
    assert viewed_again.data["data"]["browser"]
    assert _counts(eid) == (analysis_after, custody_after)


@pytest.mark.parametrize("kind", ["browser", "timeline", "metadata"])
def test_unauthorized_cannot_execute_analysis(kind, case, outsider, inv_client) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]
    analysis_before, custody_before = _counts(eid)

    other = auth_client(outsider)
    resp = other.post(f"/api/evidence/{eid}/{kind}/analyze/")
    assert resp.status_code == 403
    assert _counts(eid) == (analysis_before, custody_before)


@pytest.mark.parametrize("kind", ["browser", "timeline", "metadata"])
def test_unauthenticated_cannot_execute_analysis(kind, inv_client, case) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]
    analysis_before, custody_before = _counts(eid)

    anon = APIClient()
    resp = anon.post(f"/api/evidence/{eid}/{kind}/analyze/")
    assert resp.status_code == 401
    assert _counts(eid) == (analysis_before, custody_before)


@pytest.mark.parametrize("kind", ["browser", "timeline", "metadata"])
def test_auditor_cannot_execute_analysis_but_can_view(
    kind, auditor, inv_client, case
) -> None:
    eid = _upload(inv_client, case).data["data"]["id"]
    case.members.add(auditor)
    auditor_client = auth_client(auditor)
    analysis_before, custody_before = _counts(eid)

    viewed = auditor_client.get(f"/api/evidence/{eid}/{kind}/")
    assert viewed.status_code == 200
    assert _counts(eid) == (analysis_before, custody_before)

    denied = auditor_client.post(f"/api/evidence/{eid}/{kind}/analyze/")
    assert denied.status_code == 403
    assert _counts(eid) == (analysis_before, custody_before)


def test_postgres_database_url_parses_without_changing_sqlite_default() -> None:
    from django.conf import settings as django_settings
    from config.settings import _database_from_url

    cfg = _database_from_url(
        "postgresql://forenx:secret@db.example:5432/forenx?sslmode=require"
    )
    assert cfg["ENGINE"] == "django.db.backends.postgresql"
    assert cfg["NAME"] == "forenx"
    assert cfg["USER"] == "forenx"
    assert cfg["PASSWORD"] == "secret"
    assert cfg["HOST"] == "db.example"
    assert cfg["PORT"] == "5432"
    assert cfg["OPTIONS"]["sslmode"] == "require"
    assert django_settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
