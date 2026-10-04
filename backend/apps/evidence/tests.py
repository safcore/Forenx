import hashlib
import importlib.util
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from cases.models import Case

from apps.evidence.models import (
    AnalysisRun,
    AnalysisStatus,
    AnalysisType,
    CustodyEventRecord,
    Evidence,
    ReportRecord,
)

User = get_user_model()


class EvidenceManagementAPITests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username="investigator_a",
            email="inva@forenx.io",
            password="Pass12345!",
            role="INVESTIGATOR",
        )
        self.user_b = User.objects.create_user(
            username="investigator_b",
            email="invb@forenx.io",
            password="Pass12345!",
            role="INVESTIGATOR",
        )

        self.case_a = Case.objects.create(
            title="Operation Nightshade",
            description="Investigator A case",
            investigator=self.user_a,
        )
        self.case_b = Case.objects.create(
            title="Operation Bluefin",
            description="Investigator B case",
            investigator=self.user_b,
        )

        self.payload = b"CRITICAL FORENSIC EVIDENCE SAMPLE PAYLOAD 9876543210"
        self.expected_md5 = hashlib.md5(self.payload).hexdigest()
        self.expected_sha1 = hashlib.sha1(self.payload).hexdigest()
        self.expected_sha256 = hashlib.sha256(self.payload).hexdigest()
        self._cleanup_storage()

    def _cleanup_storage(self):
        root = Path(settings.EVIDENCE_STORAGE_DIR)
        for p in root.glob("*"):
            if p.is_file():
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)

    def tearDown(self):
        # Cleanup any physical evidence files created during testing
        for ev in Evidence.objects.all():
            if ev.stored_path and Path(ev.stored_path).exists():
                try:
                    Path(ev.stored_path).unlink(missing_ok=True)
                except Exception:
                    pass
        self._cleanup_storage()

    def _upload_sample(self, user, case_id, filename="suspect_disk.raw", content=None):
        self.client.force_authenticate(user=user)
        payload = content if content is not None else self.payload
        upload_file = SimpleUploadedFile(
            name=filename,
            content=payload,
            content_type="application/octet-stream",
        )
        return self.client.post(
            f"/api/cases/{case_id}/evidence/",
            {"file": upload_file},
            format="multipart",
        )

    def test_successful_multipart_upload_and_digests(self):
        response = self._upload_sample(self.user_a, self.case_a.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertEqual(data["case_id"], str(self.case_a.id))
        self.assertEqual(data["filename"], "suspect_disk.raw")
        self.assertEqual(data["size"], len(self.payload))
        self.assertEqual(data["hashes"]["md5"], self.expected_md5)
        self.assertEqual(data["hashes"]["sha1"], self.expected_sha1)
        self.assertEqual(data["hashes"]["sha256"], self.expected_sha256)
        self.assertEqual(data["status"], "success")

        # Database checks
        evidence = Evidence.objects.get(id=data["id"])
        self.assertEqual(evidence.case_id, self.case_a.id)
        self.assertEqual(evidence.uploaded_by, self.user_a)
        self.assertEqual(evidence.sha256, self.expected_sha256)
        self.assertTrue(Path(evidence.stored_path).is_file())

        # Custody checks: 2 genesis events created
        events = list(evidence.custody_events.order_by("timestamp", "created_at"))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].action, "evidence_uploaded")
        self.assertIsNone(events[0].previous_event_hash)
        self.assertEqual(events[1].action, "evidence_hashed")
        self.assertEqual(events[1].previous_event_hash, events[0].event_hash)

    def test_evidence_list_and_detail_with_path_redaction(self):
        res_upload = self._upload_sample(self.user_a, self.case_a.id)
        ev_id = res_upload.data["id"]

        # List for case
        res_case_list = self.client.get(f"/api/cases/{self.case_a.id}/evidence/")
        self.assertEqual(res_case_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_case_list.data), 1)
        item = res_case_list.data[0]
        self.assertEqual(item["id"], ev_id)
        self.assertTrue(item["storage_available"])
        self.assertNotIn("stored_path", item)
        self.assertNotIn("storage_name", item)
        self.assertNotIn("absolute_path", item)

        # Global list
        res_global = self.client.get("/api/evidence/")
        self.assertEqual(res_global.status_code, status.HTTP_200_OK)
        self.assertNotIn("stored_path", res_global.data[0])

        # Detail view
        res_detail = self.client.get(f"/api/evidence/{ev_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["id"], ev_id)
        self.assertNotIn("stored_path", res_detail.data)

    def test_custody_history_and_hash_chaining(self):
        res_upload = self._upload_sample(self.user_a, self.case_a.id)
        ev_id = res_upload.data["id"]

        response = self.client.get(f"/api/evidence/{ev_id}/custody/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["evidence_id"], ev_id)
        self.assertEqual(response.data["count"], 2)

        events = response.data["events"]
        self.assertIsNone(events[0]["previous_event_hash"])
        self.assertEqual(events[1]["previous_event_hash"], events[0]["event_hash"])
        self.assertEqual(len(events[0]["event_hash"]), 64)

        # Also verify custody list filtered by case_id
        res_custody_list = self.client.get(f"/api/custody/?case_id={self.case_a.id}")
        self.assertEqual(res_custody_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_custody_list.data), 2)

    def test_fast_hash_verification_success_and_mismatch(self):
        res_upload = self._upload_sample(self.user_a, self.case_a.id)
        ev_id = res_upload.data["id"]

        # Exact match
        res_match = self.client.post(
            f"/api/evidence/{ev_id}/verify-hash/",
            {"algorithm": "sha256", "expected_hash": self.expected_sha256},
            format="json",
        )
        self.assertEqual(res_match.status_code, status.HTTP_200_OK)
        self.assertTrue(res_match.data["match"])
        self.assertEqual(res_match.data["algorithm"], "sha256")

        # Case-insensitive digest match
        res_upper = self.client.post(
            f"/api/evidence/{ev_id}/verify-hash/",
            {"algorithm": "md5", "expected_hash": self.expected_md5.upper()},
            format="json",
        )
        self.assertEqual(res_upper.status_code, status.HTTP_200_OK)
        self.assertTrue(res_upper.data["match"])

        # Mismatch
        res_mismatch = self.client.post(
            f"/api/evidence/{ev_id}/verify-hash/",
            {"algorithm": "sha256", "expected_hash": "0" * 64},
            format="json",
        )
        self.assertEqual(res_mismatch.status_code, status.HTTP_200_OK)
        self.assertFalse(res_mismatch.data["match"])

    def test_physical_integrity_verification_success_and_tampered(self):
        res_upload = self._upload_sample(self.user_a, self.case_a.id)
        ev_id = res_upload.data["id"]
        evidence = Evidence.objects.get(id=ev_id)

        # Baseline check (untampered)
        res_pass = self.client.post(f"/api/evidence/{ev_id}/verify-integrity/")
        self.assertEqual(res_pass.status_code, status.HTTP_200_OK)
        self.assertTrue(res_pass.data["overall_match"])
        self.assertTrue(res_pass.data["algorithms"]["sha256"]["match"])

        # Tamper with the physical file on disk
        with open(evidence.stored_path, "wb") as f:
            f.write(b"CORRUPTED/TAMPERED FILE BY MALICIOUS ACTOR")

        # Re-verify
        res_fail = self.client.post(f"/api/evidence/{ev_id}/verify-integrity/")
        self.assertEqual(res_fail.status_code, status.HTTP_200_OK)
        self.assertFalse(res_fail.data["overall_match"])
        self.assertFalse(res_fail.data["algorithms"]["sha256"]["match"])

        # Custody event was recorded for integrity check
        custody = self.client.get(f"/api/evidence/{ev_id}/custody/")
        self.assertEqual(custody.data["count"], 4)  # upload, hash, pass-check, fail-check

    def test_rejection_of_empty_file(self):
        res = self._upload_sample(self.user_a, self.case_a.id, content=b"")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", res.data)

    def test_rejection_of_oversized_file(self):
        with patch.object(settings, "FORENX_MAX_UPLOAD_BYTES", 10):
            res = self._upload_sample(self.user_a, self.case_a.id, content=b"123456789012345")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("file", res.data)

    def test_rejection_of_blocked_extension(self):
        res = self._upload_sample(self.user_a, self.case_a.id, filename="malware.exe")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", res.data)

    def test_path_traversal_sanitization(self):
        res = self._upload_sample(
            self.user_a,
            self.case_a.id,
            filename="../../etc/passwd.bin",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        evidence = Evidence.objects.get(id=res.data["id"])
        # Original filename sanitized
        self.assertNotIn("..", evidence.original_filename)
        # Stored path strictly inside storage dir
        root = Path(settings.EVIDENCE_STORAGE_DIR).resolve()
        self.assertTrue(Path(evidence.stored_path).resolve().is_relative_to(root))

    def test_rollback_and_orphan_cleanup_on_database_failure(self):
        with patch("apps.evidence.services.Evidence.objects.create", side_effect=RuntimeError("Database failure")):
            with self.assertRaises(RuntimeError):
                self._upload_sample(self.user_a, self.case_a.id)

        # Verify no orphan evidence records
        self.assertEqual(Evidence.objects.count(), 0)
        # Verify no orphan files in storage dir
        root = Path(settings.EVIDENCE_STORAGE_DIR)
        files = list(root.glob("*"))
        self.assertEqual(len(files), 0)

    def test_append_only_custody_no_mutation_endpoints(self):
        res_upload = self._upload_sample(self.user_a, self.case_a.id)
        ev_id = res_upload.data["id"]

        # Deleting or modifying custody events is disallowed by API
        res_delete = self.client.delete(f"/api/evidence/{ev_id}/custody/")
        self.assertEqual(res_delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res_put = self.client.put(f"/api/evidence/{ev_id}/custody/", {})
        self.assertEqual(res_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res_post = self.client.post("/api/custody/", {})
        self.assertEqual(res_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_investigator_ownership_idor_isolation(self):
        # User A acquires evidence for Case A
        res_upload = self._upload_sample(self.user_a, self.case_a.id)
        ev_id = res_upload.data["id"]

        # Now authenticate as User B (investigator B)
        self.client.force_authenticate(user=self.user_b)

        # 1. User B cannot list Case A's evidence
        res_list = self.client.get(f"/api/cases/{self.case_a.id}/evidence/")
        self.assertEqual(res_list.status_code, status.HTTP_404_NOT_FOUND)

        # 2. User B cannot upload evidence into Case A
        upload_attempt = SimpleUploadedFile("hijack.raw", b"hijack", content_type="application/octet-stream")
        res_hijack = self.client.post(
            f"/api/cases/{self.case_a.id}/evidence/",
            {"file": upload_attempt},
            format="multipart",
        )
        self.assertEqual(res_hijack.status_code, status.HTTP_404_NOT_FOUND)

        # 3. User B cannot view User A's evidence detail
        res_detail = self.client.get(f"/api/evidence/{ev_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

        # 4. User B cannot view User A's custody history
        res_custody = self.client.get(f"/api/evidence/{ev_id}/custody/")
        self.assertEqual(res_custody.status_code, status.HTTP_404_NOT_FOUND)

        # 5. User B cannot trigger hash verification on User A's evidence
        res_verify_h = self.client.post(
            f"/api/evidence/{ev_id}/verify-hash/",
            {"algorithm": "sha256", "expected_hash": self.expected_sha256},
            format="json",
        )
        self.assertEqual(res_verify_h.status_code, status.HTTP_404_NOT_FOUND)

        # 6. User B cannot trigger physical integrity check on User A's evidence
        res_verify_i = self.client.post(f"/api/evidence/{ev_id}/verify-integrity/")
        self.assertEqual(res_verify_i.status_code, status.HTTP_404_NOT_FOUND)

        # 7. User B global evidence list and custody list do NOT include User A's data
        res_global_ev = self.client.get("/api/evidence/")
        self.assertEqual(len(res_global_ev.data), 0)

        res_global_custody = self.client.get(f"/api/custody/?case_id={self.case_a.id}")
        self.assertEqual(len(res_global_custody.data), 0)


def _build_test_chrome_profile(target_dir: Path) -> Path:
    fixtures_path = (
        Path(settings.BASE_DIR).parent
        / "forensics"
        / "forenx-forensics"
        / "tests"
        / "browser_fixtures.py"
    )
    spec = importlib.util.spec_from_file_location("test_fixtures_browser", fixtures_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_chromium_profile(target_dir)


class ForensicAnalysisAPITests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username="analyst_alpha",
            email="alpha@forenx.io",
            password="Pass12345!",
            role="INVESTIGATOR",
        )
        self.user_b = User.objects.create_user(
            username="analyst_beta",
            email="beta@forenx.io",
            password="Pass12345!",
            role="INVESTIGATOR",
        )

        self.case_a = Case.objects.create(
            title="Operation Shadowgate",
            description="Investigator A incident case",
            investigator=self.user_a,
        )
        self.case_b = Case.objects.create(
            title="Operation Silverline",
            description="Investigator B incident case",
            investigator=self.user_b,
        )

        self.text_content = (
            b"Incident Report: High severity exploit detected.\n"
            b"Suspicious bitcoin malware payload found in user system.\n"
            b"Confidential token leaked during unauthorized session.\n"
        )

    def tearDown(self):
        report_root = Path(settings.REPORT_STORAGE_DIR).resolve()
        evidence_root = Path(settings.EVIDENCE_STORAGE_DIR).resolve()
        for ev in Evidence.objects.all():
            if ev.stored_path:
                try:
                    p = Path(ev.stored_path).resolve()
                    if p.is_relative_to(evidence_root) and p.is_file():
                        p.unlink(missing_ok=True)
                except Exception:
                    pass
        for rep in ReportRecord.objects.all():
            for p_str in (rep.json_path, rep.pdf_path):
                if p_str:
                    try:
                        p = Path(p_str).resolve()
                        if p.is_relative_to(report_root) and p.is_file():
                            p.unlink(missing_ok=True)
                    except Exception:
                        pass

    def _upload(self, user, case_id, filename="log.txt", content=None):
        self.client.force_authenticate(user=user)
        payload = content if content is not None else self.text_content
        f = SimpleUploadedFile(filename, payload, content_type="text/plain")
        res = self.client.post(
            f"/api/cases/{case_id}/evidence/",
            {"file": f},
            format="multipart",
        )
        return res

    def test_metadata_analysis_post_and_cached_get_and_path_redaction(self):
        upload_res = self._upload(self.user_a, self.case_a.id)
        self.assertEqual(upload_res.status_code, status.HTTP_201_CREATED)
        ev_id = upload_res.data["id"]

        # Initial GET before analysis returns status "not_performed"
        get_init = self.client.get(f"/api/evidence/{ev_id}/metadata/")
        self.assertEqual(get_init.status_code, status.HTTP_200_OK)
        self.assertTrue(get_init.data["success"])
        self.assertEqual(get_init.data["data"]["status"], "not_performed")

        runs_before = AnalysisRun.objects.filter(evidence_id=ev_id).count()
        custody_before = CustodyEventRecord.objects.filter(evidence_id=ev_id).count()

        # POST executes metadata analysis
        post_res = self.client.post(f"/api/evidence/{ev_id}/metadata/analyze/")
        self.assertEqual(post_res.status_code, status.HTTP_200_OK)
        self.assertTrue(post_res.data["success"])
        meta_data = post_res.data["data"]
        self.assertEqual(meta_data["file_type"], "filesystem")
        self.assertIn("analyzed_at", meta_data)
        self.assertIn("metadata_categories", meta_data)
        self.assertIn("filesystem", meta_data)

        # Path redaction check: no sensitive path keys exposed
        self.assertNotIn("stored_path", meta_data)
        self.assertNotIn("absolute_path", meta_data)
        if meta_data.get("filesystem"):
            self.assertNotIn("absolute_path", meta_data["filesystem"])
            self.assertNotIn("stored_path", meta_data["filesystem"])

        # DB verification: 1 AnalysisRun created with status SUCCESS
        self.assertEqual(
            AnalysisRun.objects.filter(evidence_id=ev_id).count(),
            runs_before + 1,
        )
        run = AnalysisRun.objects.get(evidence_id=ev_id, analysis_type="metadata")
        self.assertEqual(run.status, "success")
        self.assertEqual(run.created_by, self.user_a)

        # Custody verification: 1 new custody event created
        self.assertEqual(
            CustodyEventRecord.objects.filter(evidence_id=ev_id).count(),
            custody_before + 1,
        )
        last_custody = CustodyEventRecord.objects.filter(evidence_id=ev_id).last()
        self.assertEqual(last_custody.action, "evidence_analyzed")

        # GET returns cached result without running analysis again
        get_again = self.client.get(f"/api/evidence/{ev_id}/metadata/")
        self.assertEqual(get_again.status_code, status.HTTP_200_OK)
        self.assertEqual(get_again.data["data"]["file_type"], "filesystem")
        self.assertEqual(
            AnalysisRun.objects.filter(evidence_id=ev_id).count(),
            runs_before + 1,
        )
        self.assertEqual(
            CustodyEventRecord.objects.filter(evidence_id=ev_id).count(),
            custody_before + 1,
        )

    def test_keyword_search_analysis_and_validation(self):
        upload_res = self._upload(self.user_a, self.case_a.id)
        ev_id = upload_res.data["id"]

        runs_before = AnalysisRun.objects.filter(evidence_id=ev_id).count()
        custody_before = CustodyEventRecord.objects.filter(evidence_id=ev_id).count()

        # Valid multi-keyword search
        res = self.client.post(
            f"/api/evidence/{ev_id}/keywords/",
            {"keywords": ["malware", "exploit", "bitcoin"]},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        data = res.data["data"]
        self.assertEqual(data["match_count"], 3)
        self.assertEqual(len(data["matches"]), 3)
        self.assertIn("searched_at", data)
        self.assertNotIn("absolute_path", data)

        # AnalysisRun and Custody verified
        self.assertEqual(
            AnalysisRun.objects.filter(evidence_id=ev_id, analysis_type="keyword").count(),
            1,
        )
        self.assertEqual(
            CustodyEventRecord.objects.filter(evidence_id=ev_id).count(),
            custody_before + 1,
        )
        custody_ev = CustodyEventRecord.objects.filter(evidence_id=ev_id).last()
        self.assertEqual(custody_ev.action, "evidence_analyzed")
        self.assertEqual(custody_ev.metadata.get("match_count"), 3)

        # Validation: empty keywords
        res_empty = self.client.post(
            f"/api/evidence/{ev_id}/keywords/",
            {"keywords": []},
            format="json",
        )
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)

        # Validation: keyword too long (>128 chars)
        res_long = self.client.post(
            f"/api/evidence/{ev_id}/keywords/",
            {"keywords": ["a" * 129]},
            format="json",
        )
        self.assertEqual(res_long.status_code, status.HTTP_400_BAD_REQUEST)

        # Validation: invalid regex
        res_regex = self.client.post(
            f"/api/evidence/{ev_id}/keywords/",
            {"keywords": ["(unclosed_group"], "regex": True},
            format="json",
        )
        self.assertEqual(res_regex.status_code, status.HTTP_400_BAD_REQUEST)

    def test_browser_analysis_rejection_and_execution(self):
        # 1. Non-browser file rejection
        upload_txt = self._upload(self.user_a, self.case_a.id)
        txt_id = upload_txt.data["id"]
        res_txt = self.client.post(f"/api/evidence/{txt_id}/browser/analyze/")
        self.assertEqual(res_txt.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Build synthetic chromium profile in isolated temp dir
        temp_profile_dir = tempfile.mkdtemp(prefix="forenx_test_browser_")
        try:
            tmp_dir = Path(temp_profile_dir)
            profile_path = _build_test_chrome_profile(tmp_dir)
            history_file = profile_path / "History"

            # Point an evidence record at the History file
            evidence = Evidence.objects.get(id=txt_id)
            evidence.stored_path = str(history_file)
            evidence.original_filename = "History"
            evidence.save(update_fields=["stored_path", "original_filename"])

            # GET before analyze returns not_performed
            get_before = self.client.get(f"/api/evidence/{txt_id}/browser/")
            self.assertEqual(get_before.status_code, status.HTTP_200_OK)
            self.assertEqual(get_before.data["data"]["status"], "not_performed")

            # POST executes browser analysis
            res_analyze = self.client.post(f"/api/evidence/{txt_id}/browser/analyze/")
            self.assertEqual(res_analyze.status_code, status.HTTP_200_OK)
            data = res_analyze.data["data"]
            self.assertEqual(data["browser"], "chrome")
            self.assertIn("history", data)
            self.assertIn("downloads", data)
            self.assertIn("cookies", data)
            self.assertIn("summary", data)

            # Verify NO cookie values in cookies list (critical security requirement)
            for cookie in data.get("cookies", []):
                self.assertNotIn("value", cookie)

            # Verify AnalysisRun and custody created
            self.assertEqual(
                AnalysisRun.objects.filter(evidence_id=txt_id, analysis_type="browser").count(),
                1,
            )
            last_custody = CustodyEventRecord.objects.filter(evidence_id=txt_id).last()
            self.assertEqual(last_custody.action, "evidence_analyzed")

            # GET returns cached result
            get_cached = self.client.get(f"/api/evidence/{txt_id}/browser/")
            self.assertEqual(get_cached.status_code, status.HTTP_200_OK)
            self.assertEqual(get_cached.data["data"]["browser"], "chrome")
        finally:
            shutil.rmtree(temp_profile_dir, ignore_errors=True)

    def test_timeline_analysis_and_ordering(self):
        upload_res = self._upload(self.user_a, self.case_a.id)
        ev_id = upload_res.data["id"]

        # Initial GET returns not_performed
        get_before = self.client.get(f"/api/evidence/{ev_id}/timeline/")
        self.assertEqual(get_before.status_code, status.HTTP_200_OK)
        self.assertEqual(get_before.data["data"]["status"], "not_performed")

        # POST executes timeline analysis
        res = self.client.post(f"/api/evidence/{ev_id}/timeline/analyze/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        data = res.data["data"]
        events = data["events"]
        self.assertGreaterEqual(len(events), 1)
        self.assertIn("summary", data)
        self.assertIn("total_events", data["summary"])

        # Verify chronological ordering
        timestamps = [e["timestamp"] for e in events if "timestamp" in e]
        self.assertEqual(timestamps, sorted(timestamps))

        # Verify source_file contains basename only
        for ev in events:
            if ev.get("source_file"):
                self.assertNotIn("/", ev["source_file"])
                self.assertNotIn("\\", ev["source_file"])

        # Custody created
        last_custody = CustodyEventRecord.objects.filter(evidence_id=ev_id).last()
        self.assertEqual(last_custody.action, "evidence_analyzed")

        # GET returns cached result
        get_cached = self.client.get(f"/api/evidence/{ev_id}/timeline/")
        self.assertEqual(get_cached.status_code, status.HTTP_200_OK)
        self.assertEqual(len(get_cached.data["data"]["events"]), len(events))

    def test_report_generation_and_authenticated_download(self):
        upload_res = self._upload(self.user_a, self.case_a.id)
        ev_id = upload_res.data["id"]

        # Run metadata analysis and keyword search first
        self.client.post(f"/api/evidence/{ev_id}/metadata/analyze/")
        self.client.post(
            f"/api/evidence/{ev_id}/keywords/",
            {"keywords": ["malware"]},
            format="json",
        )

        # POST /report/ with format="both"
        res_report = self.client.post(
            f"/api/evidence/{ev_id}/report/",
            {"format": "both"},
            format="json",
        )
        self.assertEqual(res_report.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_report.data["success"])
        data = res_report.data["data"]
        self.assertTrue(data["has_json"])
        self.assertTrue(data["has_pdf"])
        self.assertIn("download_url", data)
        report_db_id = data["id"]

        # DB ReportRecord verified
        record = ReportRecord.objects.get(id=report_db_id)
        self.assertEqual(record.case, self.case_a)
        self.assertEqual(str(record.evidence_id), ev_id)
        self.assertTrue(Path(record.json_path).is_file())
        self.assertTrue(Path(record.pdf_path).is_file())

        # Custody event: EVIDENCE_EXPORTED
        last_custody = CustodyEventRecord.objects.filter(evidence_id=ev_id).last()
        self.assertEqual(last_custody.action, "evidence_exported")

        # Authenticated download: PDF
        res_dl_pdf = self.client.get(f"/api/reports/{report_db_id}/download/?format=pdf")
        self.assertEqual(res_dl_pdf.status_code, status.HTTP_200_OK)
        self.assertEqual(res_dl_pdf["Content-Type"], "application/pdf")

        # Authenticated download: JSON
        res_dl_json = self.client.get(f"/api/reports/{report_db_id}/download/?format=json")
        self.assertEqual(res_dl_json.status_code, status.HTTP_200_OK)
        self.assertEqual(res_dl_json["Content-Type"], "application/json")

        # GET /api/reports/ list endpoint
        res_list = self.client.get("/api/reports/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_list.data["data"]), 1)
        self.assertEqual(res_list.data["data"][0]["id"], report_db_id)

        # Path traversal protection: tampered path returns 404
        record.pdf_path = str(Path(settings.BASE_DIR) / "outside_secret.pdf")
        record.save(update_fields=["pdf_path"])
        res_tamper = self.client.get(f"/api/reports/{report_db_id}/download/?format=pdf")
        self.assertEqual(res_tamper.status_code, status.HTTP_404_NOT_FOUND)

    def test_ai_assist_analysis_offline_and_advisory(self):
        upload_res = self._upload(self.user_a, self.case_a.id)
        ev_id = upload_res.data["id"]

        # Run keyword search so AI context has findings
        self.client.post(
            f"/api/evidence/{ev_id}/keywords/",
            {"keywords": ["bitcoin", "malware"]},
            format="json",
        )

        # POST /ai-assist/
        res_ai = self.client.post(
            f"/api/evidence/{ev_id}/ai-assist/",
            {"question": "What notable correlations exist between findings?"},
            format="json",
        )
        self.assertEqual(res_ai.status_code, status.HTTP_200_OK)
        self.assertTrue(res_ai.data["success"])
        data = res_ai.data["data"]
        self.assertTrue(data["advisory_only"])
        self.assertIn("disclaimer", data)
        self.assertIn(data["provider"], ["local", "deterministic"])
        self.assertIn("summary", data)
        self.assertIn("observations", data)

        # Verify custody event
        last_custody = CustodyEventRecord.objects.filter(evidence_id=ev_id).last()
        self.assertEqual(last_custody.action, "ai_analysis_performed")

        # Question validation: question > 1000 chars
        res_toolong = self.client.post(
            f"/api/evidence/{ev_id}/ai-assist/",
            {"question": "q" * 1001},
            format="json",
        )
        self.assertEqual(res_toolong.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analysis_history_lifecycle_and_error_handling(self):
        upload_res = self._upload(self.user_a, self.case_a.id)
        ev_id = upload_res.data["id"]

        self.client.post(f"/api/evidence/{ev_id}/metadata/analyze/")
        self.client.post(
            f"/api/evidence/{ev_id}/keywords/",
            {"keywords": ["malware"]},
            format="json",
        )

        # History list
        res_hist = self.client.get(f"/api/evidence/{ev_id}/analysis-runs/")
        self.assertEqual(res_hist.status_code, status.HTTP_200_OK)
        runs = res_hist.data["data"]
        self.assertGreaterEqual(len(runs), 2)
        for r in runs:
            self.assertIn("id", r)
            self.assertIn("analysis_type", r)
            self.assertIn("status", r)
            self.assertIn("result_summary", r)

        # Simulate failed run: error message is safe without tracebacks
        failed_run = AnalysisRun.objects.create(
            case=self.case_a,
            evidence_id=ev_id,
            analysis_type="metadata",
            status="failed",
            error_message="Traceback (most recent call last):\nFile 'secret.py'\nValueError: Bad parser",
            created_by=self.user_a,
        )
        res_failed = self.client.get(f"/api/evidence/{ev_id}/analysis-runs/")
        failed_item = next(item for item in res_failed.data["data"] if item["id"] == str(failed_run.id))
        self.assertNotIn("Traceback", failed_item["error_message"])

    def test_cross_investigator_security_and_idor_protection(self):
        # User A acquires evidence and generates report
        upload_res = self._upload(self.user_a, self.case_a.id)
        ev_id = upload_res.data["id"]
        res_rep = self.client.post(
            f"/api/evidence/{ev_id}/report/",
            {"format": "both"},
            format="json",
        )
        rep_id = res_rep.data["data"]["id"]

        # Authenticate as User B (investigator B)
        self.client.force_authenticate(user=self.user_b)

        # All analysis POST endpoints return 404
        self.assertEqual(
            self.client.post(f"/api/evidence/{ev_id}/metadata/analyze/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(
                f"/api/evidence/{ev_id}/keywords/",
                {"keywords": ["test"]},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(f"/api/evidence/{ev_id}/browser/analyze/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(f"/api/evidence/{ev_id}/timeline/analyze/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(
                f"/api/evidence/{ev_id}/report/",
                {"format": "both"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(
                f"/api/evidence/{ev_id}/ai-assist/",
                {"question": "test"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # All analysis GET endpoints return 404
        self.assertEqual(
            self.client.get(f"/api/evidence/{ev_id}/metadata/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get(f"/api/evidence/{ev_id}/browser/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get(f"/api/evidence/{ev_id}/timeline/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get(f"/api/evidence/{ev_id}/analysis-runs/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get(f"/api/reports/{rep_id}/download/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # User B reports list does NOT include User A's reports
        res_list_b = self.client.get("/api/reports/")
        self.assertEqual(len(res_list_b.data["data"]), 0)


class SupabaseStorageIntegrationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supabase_investigator",
            email="sb_inv@forenx.io",
            password="Pass12345!",
            role="INVESTIGATOR",
        )
        self.case = Case.objects.create(
            title="Operation Cloudtrail",
            description="Supabase test case",
            investigator=self.user,
        )
        self.payload = b"SUPABASE CLOUD PERSISTENT EVIDENCE CONTENT 12345"
        self.expected_md5 = hashlib.md5(self.payload).hexdigest()
        self.expected_sha1 = hashlib.sha1(self.payload).hexdigest()
        self.expected_sha256 = hashlib.sha256(self.payload).hexdigest()
        self._cleanup_storage()

    def _cleanup_storage(self):
        root = Path(settings.EVIDENCE_STORAGE_DIR)
        for p in root.glob("*"):
            if p.is_file():
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)

    def tearDown(self):
        for ev in Evidence.objects.all():
            if ev.stored_path and Path(ev.stored_path).exists():
                try:
                    Path(ev.stored_path).unlink(missing_ok=True)
                except Exception:
                    pass
        self._cleanup_storage()

    def _upload_file(self, content=None, filename="cloud_disk.raw"):
        self.client.force_authenticate(user=self.user)
        payload = content if content is not None else self.payload
        upload_file = SimpleUploadedFile(
            name=filename,
            content=payload,
            content_type="application/octet-stream",
        )
        return self.client.post(
            f"/api/cases/{self.case.id}/evidence/",
            {"file": upload_file},
            format="multipart",
        )

    def test_configuration_detection_and_fallback(self):
        from apps.evidence.storage import is_supabase_storage_enabled

        with patch.object(settings, "SUPABASE_URL", None), \
             patch.object(settings, "SUPABASE_SECRET_KEY", None):
            self.assertFalse(is_supabase_storage_enabled())

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            self.assertTrue(is_supabase_storage_enabled())

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "local"):
            self.assertFalse(is_supabase_storage_enabled())

    @patch("apps.evidence.storage.get_supabase_client")
    def test_upload_with_supabase_storage_enabled(self, mock_get_client):
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.storage.from_.return_value = mock_bucket
        mock_get_client.return_value = mock_client

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            response = self._upload_file()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data["hashes"]["sha256"], self.expected_sha256)

        evidence = Evidence.objects.get(id=data["id"])
        mock_client.storage.from_.assert_called_with("evidence")
        mock_bucket.upload.assert_called_once()
        call_kwargs = mock_bucket.upload.call_args.kwargs
        self.assertEqual(call_kwargs["path"], evidence.storage_name)

    @patch("apps.evidence.storage.get_supabase_client")
    def test_upload_failure_rolls_back_and_cleans_up(self, mock_get_client):
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.upload.side_effect = Exception("Supabase network error")
        mock_client.storage.from_.return_value = mock_bucket
        mock_get_client.return_value = mock_client

        initial_count = Evidence.objects.count()

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            response = self._upload_file()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)
        self.assertIn("Failed to persist evidence to cloud storage.", str(response.data["file"]))
        self.assertEqual(Evidence.objects.count(), initial_count)

    @patch("apps.evidence.storage.get_supabase_client")
    def test_ensure_local_evidence_file_local_vs_remote(self, mock_get_client):
        from apps.evidence.storage import ensure_local_evidence_file

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.storage.from_.return_value = mock_bucket
        mock_get_client.return_value = mock_client

        res = self._upload_file()
        evidence = Evidence.objects.get(id=res.data["id"])
        self.assertTrue(Path(evidence.stored_path).is_file())

        # Calling ensure_local_evidence_file when local file exists does not call Supabase
        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            path1 = ensure_local_evidence_file(evidence)
            self.assertEqual(path1, Path(evidence.stored_path))
            mock_bucket.download.assert_not_called()

            # Simulate ephemeral disk loss: delete local file
            Path(evidence.stored_path).unlink()
            self.assertFalse(Path(evidence.stored_path).exists())

            # Configure mock download
            mock_bucket.download.return_value = self.payload

            # Calling ensure_local_evidence_file retrieves from Supabase
            path2 = ensure_local_evidence_file(evidence)
            self.assertTrue(path2.is_file())
            self.assertEqual(path2.read_bytes(), self.payload)
            mock_bucket.download.assert_called_once_with(evidence.storage_name)

    @patch("apps.evidence.storage.get_supabase_client")
    def test_storage_available_serializer_logic(self, mock_get_client):
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.storage.from_.return_value = mock_bucket
        mock_get_client.return_value = mock_client

        res = self._upload_file()
        ev_id = res.data["id"]
        evidence = Evidence.objects.get(id=ev_id)

        # Remove local file
        Path(evidence.stored_path).unlink()

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            # Mock object exists in Supabase
            mock_bucket.exists.return_value = True
            detail_res1 = self.client.get(f"/api/evidence/{ev_id}/")
            self.assertTrue(detail_res1.data["storage_available"])

            # Mock object missing in Supabase
            mock_bucket.exists.return_value = False
            detail_res2 = self.client.get(f"/api/evidence/{ev_id}/")
            self.assertFalse(detail_res2.data["storage_available"])

    @patch("apps.evidence.storage.get_supabase_client")
    def test_integrity_verification_restores_from_cloud(self, mock_get_client):
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.download.return_value = self.payload
        mock_client.storage.from_.return_value = mock_bucket
        mock_get_client.return_value = mock_client

        res = self._upload_file()
        ev_id = res.data["id"]
        evidence = Evidence.objects.get(id=ev_id)

        # Remove local file to simulate container restart
        Path(evidence.stored_path).unlink()

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            verify_res = self.client.post(f"/api/evidence/{ev_id}/verify-integrity/")
            self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
            self.assertTrue(verify_res.data["overall_match"])
            mock_bucket.download.assert_called_with(evidence.storage_name)

    @patch("apps.evidence.storage.get_supabase_client")
    def test_forensic_analysis_restores_from_cloud(self, mock_get_client):
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        sample_text = b"CONFIDENTIAL INVESTIGATION SUSPECT INTEL"
        mock_bucket.download.return_value = sample_text
        mock_client.storage.from_.return_value = mock_bucket
        mock_get_client.return_value = mock_client

        res = self._upload_file(content=sample_text, filename="notes.txt")
        ev_id = res.data["id"]
        evidence = Evidence.objects.get(id=ev_id)

        Path(evidence.stored_path).unlink()

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            kw_res = self.client.post(
                f"/api/evidence/{ev_id}/keywords/",
                {"keywords": ["CONFIDENTIAL"]},
                format="json",
            )
            self.assertEqual(kw_res.status_code, status.HTTP_200_OK)
            self.assertEqual(kw_res.data["data"]["match_count"], 1)

    @patch("apps.evidence.storage.get_supabase_client")
    def test_download_failure_returns_not_found(self, mock_get_client):
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.download.side_effect = Exception("Storage error 404")
        mock_client.storage.from_.return_value = mock_bucket
        mock_get_client.return_value = mock_client

        res = self._upload_file()
        ev_id = res.data["id"]
        evidence = Evidence.objects.get(id=ev_id)

        Path(evidence.stored_path).unlink()

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            verify_res = self.client.post(f"/api/evidence/{ev_id}/verify-integrity/")
            self.assertEqual(verify_res.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn("Evidence file could not be retrieved from persistent storage.", str(verify_res.data))

    @patch("apps.evidence.storage.get_supabase_client")
    def test_delete_storage_file_removes_from_supabase(self, mock_get_client):
        from apps.evidence.storage import delete_storage_file

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.storage.from_.return_value = mock_bucket
        mock_get_client.return_value = mock_client

        with patch.object(settings, "SUPABASE_URL", "https://example.supabase.co"), \
             patch.object(settings, "SUPABASE_SECRET_KEY", "secret_key_123"), \
             patch.object(settings, "FORENX_STORAGE_BACKEND", "supabase"):
            delete_storage_file(None, storage_name="test_storage_name.bin")
            mock_bucket.remove.assert_called_once_with(["test_storage_name.bin"])
