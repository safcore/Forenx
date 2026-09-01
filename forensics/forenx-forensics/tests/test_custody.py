"""Tests for Phase 7 chain-of-custody / evidence audit trail."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.custody.event_builder import build_custody_event
from app.custody.models import event_hash_from_fields
from app.custody.verifier import verify_custody_chain
from app.schemas.custody import (
    CustodyAction,
    CustodyStatus,
    EvidenceIntegrityStatus,
)
from app.services.custody_service import CustodyService
from app.services.hash_service import HashService
from app.utils.exceptions import CustodyError


@pytest.fixture
def custody_service() -> CustodyService:
    """Return an isolated CustodyService with a fresh ledger."""
    return CustodyService()


@pytest.fixture
def sample_sha256() -> str:
    """Return a syntactically valid SHA-256 digest."""
    return "a" * 64


def _record_chain(service: CustodyService, sha256: str) -> None:
    base = datetime(2024, 7, 1, 10, 0, tzinfo=timezone.utc)
    service.record_event(
        evidence_id="EV-001",
        action=CustodyAction.EVIDENCE_ACQUIRED,
        description="Acquired disk image",
        actor_id="inv-1",
        actor_role="investigator",
        source="django",
        source_ip="203.0.113.10",
        evidence_sha256=sha256,
        evidence_path="evidence/sample_case/sample_evidence.txt",
        original_filename="sample_evidence.txt",
        metadata={"case": "CASE-9"},
        timestamp=base,
    )
    service.record_event(
        evidence_id="EV-001",
        action=CustodyAction.EVIDENCE_EXAMINED,
        description="Initial examination",
        actor_id="inv-1",
        actor_role="investigator",
        evidence_sha256=sha256,
        timestamp=base + timedelta(hours=1),
    )
    service.record_event(
        evidence_id="EV-001",
        action=CustodyAction.EVIDENCE_ANALYZED,
        description="Hash and metadata analysis",
        actor_id="an-2",
        actor_role="analyst",
        evidence_sha256=sha256,
        timestamp=base + timedelta(hours=2),
    )


class TestCustodyEventCreation:
    def test_create_first_custody_event(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        event = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_ACQUIRED,
            description="Seized laptop",
            actor_id="admin-1",
            actor_role="administrator",
            evidence_sha256=sample_sha256,
        )
        assert event.evidence_id == "EV-001"
        assert event.action is CustodyAction.EVIDENCE_ACQUIRED
        assert event.event_id

    def test_first_event_has_no_previous_hash(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        event = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_REGISTERED,
            description="Registered evidence",
            evidence_sha256=sample_sha256,
        )
        assert event.previous_event_hash is None

    def test_first_event_has_valid_event_hash(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        event = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_UPLOADED,
            description="Uploaded evidence",
            evidence_sha256=sample_sha256,
        )
        expected = event_hash_from_fields(
            event_id=event.event_id,
            evidence_id=event.evidence_id,
            action=event.action,
            timestamp=event.timestamp,
            actor_id=event.actor_id,
            actor_role=event.actor_role,
            source=event.source,
            source_ip=event.source_ip,
            description=event.description,
            evidence_sha256=event.evidence_sha256,
            previous_event_hash=event.previous_event_hash,
            metadata=event.metadata,
            evidence_path=event.evidence_path,
            original_filename=event.original_filename,
            file_size=event.file_size,
        )
        assert event.event_hash == expected
        assert len(event.event_hash) == 64


class TestHashChaining:
    def test_append_second_event_links_previous(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        first = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_ACQUIRED,
            description="Acquired",
            evidence_sha256=sample_sha256,
        )
        second = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_HASHED,
            description="Hashed",
            evidence_sha256=sample_sha256,
        )
        assert second.previous_event_hash == first.event_hash

    def test_append_multiple_events(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        assert len(custody_service.get_chain("EV-001")) == 3

    def test_chain_verifies_successfully(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = custody_service.verify_chain("EV-001")
        assert result.valid is True
        assert result.event_count == 3
        assert result.status is CustodyStatus.VALID
        assert result.broken_event_id is None


class TestTamperDetection:
    def _mutated_chain(self, service: CustodyService, **updates):
        chain = service.get_chain("EV-001")
        mutated = [item.model_copy(deep=True) for item in chain]
        mutated[1] = mutated[1].model_copy(update=updates)
        return mutated

    def test_tampered_action_detected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = verify_custody_chain(
            self._mutated_chain(
                custody_service, action=CustodyAction.EVIDENCE_CLOSED
            )
        )
        assert result.valid is False
        assert result.broken_event_id is not None

    def test_tampered_timestamp_detected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = verify_custody_chain(
            self._mutated_chain(
                custody_service,
                timestamp=datetime(2099, 1, 1, tzinfo=timezone.utc),
            )
        )
        assert result.valid is False

    def test_tampered_actor_detected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = verify_custody_chain(
            self._mutated_chain(custody_service, actor_id="intruder")
        )
        assert result.valid is False

    def test_tampered_evidence_hash_detected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = verify_custody_chain(
            self._mutated_chain(custody_service, evidence_sha256="b" * 64)
        )
        assert result.valid is False

    def test_tampered_description_detected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = verify_custody_chain(
            self._mutated_chain(custody_service, description="altered")
        )
        assert result.valid is False

    def test_tampered_metadata_detected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = verify_custody_chain(
            self._mutated_chain(custody_service, metadata={"case": "TAMPERED"})
        )
        assert result.valid is False

    def test_tampered_previous_hash_detected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = verify_custody_chain(
            self._mutated_chain(custody_service, previous_event_hash="c" * 64)
        )
        assert result.valid is False

    def test_tampered_event_hash_detected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = verify_custody_chain(
            self._mutated_chain(custody_service, event_hash="d" * 64)
        )
        assert result.valid is False


class TestValidation:
    def test_duplicate_event_id_rejected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        first = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_ACQUIRED,
            description="first",
            evidence_sha256=sample_sha256,
            event_id="fixed-event-id",
        )
        assert first.event_id == "fixed-event-id"
        with pytest.raises(CustodyError, match="Duplicate"):
            custody_service.record_event(
                evidence_id="EV-001",
                action=CustodyAction.EVIDENCE_EXAMINED,
                description="second",
                evidence_sha256=sample_sha256,
                event_id="fixed-event-id",
            )

    def test_invalid_sha256_rejected(self, custody_service: CustodyService) -> None:
        with pytest.raises(CustodyError, match="Invalid evidence_sha256"):
            custody_service.record_event(
                evidence_id="EV-001",
                action=CustodyAction.EVIDENCE_HASHED,
                description="bad hash",
                evidence_sha256="not-hex",
            )

    def test_missing_evidence_id_rejected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        with pytest.raises(CustodyError, match="evidence_id"):
            custody_service.record_event(
                evidence_id="  ",
                action=CustodyAction.EVIDENCE_ACQUIRED,
                description="missing id",
                evidence_sha256=sample_sha256,
            )

    def test_missing_action_rejected(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        with pytest.raises(CustodyError, match="action"):
            custody_service.record_event(
                evidence_id="EV-001",
                action="   ",
                description="missing action",
                evidence_sha256=sample_sha256,
            )

    def test_missing_actor_handled_correctly(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        event = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_ACCESSED,
            description="System automated access note",
            evidence_sha256=sample_sha256,
            actor_id=None,
            actor_role=None,
        )
        assert event.actor_id is None
        assert event.actor_role is None
        assert custody_service.verify_chain("EV-001").valid is True


class TestEvidenceIntegrity:
    def test_evidence_integrity_pass(
        self, custody_service: CustodyService, tmp_path: Path
    ) -> None:
        path = tmp_path / "evidence.bin"
        path.write_bytes(b"forenx-custody-integrity")
        digest = next(
            item.hash
            for item in HashService().calculate_hashes(path)
            if item.algorithm == "sha256"
        )
        custody_service.record_event(
            evidence_id="EV-INT",
            action=CustodyAction.EVIDENCE_HASHED,
            description="Hashed sample",
            evidence_sha256=digest,
            evidence_path=str(path),
        )
        result = custody_service.verify_evidence_integrity(
            path, digest, evidence_id="EV-INT"
        )
        assert result.status is EvidenceIntegrityStatus.VERIFIED
        assert result.verified is True

    def test_evidence_integrity_fail(
        self, custody_service: CustodyService, tmp_path: Path
    ) -> None:
        path = tmp_path / "evidence.bin"
        path.write_bytes(b"original")
        result = custody_service.verify_evidence_integrity(path, "e" * 64)
        assert result.status is EvidenceIntegrityStatus.MISMATCH
        assert result.verified is False

    def test_missing_evidence_integrity_check(
        self, custody_service: CustodyService
    ) -> None:
        result = custody_service.verify_evidence_integrity(
            "missing/file.bin", "f" * 64
        )
        assert result.status is EvidenceIntegrityStatus.MISSING
        assert result.verified is False


class TestServiceOrchestration:
    def test_latest_event_retrieval(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        latest = custody_service.get_latest_event("EV-001")
        assert latest is not None
        assert latest.action is CustodyAction.EVIDENCE_ANALYZED

    def test_chain_ordering(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        chain = custody_service.get_chain("EV-001")
        assert [item.action for item in chain] == [
            CustodyAction.EVIDENCE_ACQUIRED,
            CustodyAction.EVIDENCE_EXAMINED,
            CustodyAction.EVIDENCE_ANALYZED,
        ]
        for index in range(1, len(chain)):
            assert chain[index].previous_event_hash == chain[index - 1].event_hash

    def test_structured_verification_result(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        result = custody_service.verify_chain("EV-001")
        assert result.first_event is not None
        assert result.last_event is not None
        assert isinstance(result.message, str)
        assert isinstance(result.warnings, list)

    def test_append_only_behavior(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_ACQUIRED,
            description="acquired",
            evidence_sha256=sample_sha256,
        )
        assert not hasattr(custody_service, "update_event")
        assert not hasattr(custody_service, "delete_event")
        with pytest.raises(CustodyError, match="append-only"):
            custody_service.assert_append_only()

    def test_corrective_event_can_be_appended(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        _record_chain(custody_service, sample_sha256)
        corrective = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_EXAMINED,
            description="Corrective note clarifying prior examination scope",
            actor_id="lead-1",
            actor_role="lead_investigator",
            evidence_sha256=sample_sha256,
            metadata={"corrective": True},
        )
        assert corrective.previous_event_hash is not None
        assert custody_service.verify_chain("EV-001").valid is True
        assert len(custody_service.get_chain("EV-001")) == 4

    def test_timezone_aware_timestamps(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        event = custody_service.record_event(
            evidence_id="EV-001",
            action=CustodyAction.EVIDENCE_ACQUIRED,
            description="aware",
            evidence_sha256=sample_sha256,
            timestamp=datetime(2024, 1, 1, 8, 30, tzinfo=timezone.utc),
        )
        assert event.timestamp.tzinfo is not None
        with pytest.raises(CustodyError, match="timezone-aware"):
            build_custody_event(
                evidence_id="EV-002",
                action=CustodyAction.EVIDENCE_ACQUIRED,
                description="naive rejected",
                evidence_sha256=sample_sha256,
                timestamp=datetime(2024, 1, 1, 8, 30),
            )

    def test_deterministic_event_hash(self, sample_sha256: str) -> None:
        ts = datetime(2024, 3, 4, 5, 6, 7, tzinfo=timezone.utc)
        first = build_custody_event(
            evidence_id="EV-DET",
            action=CustodyAction.EVIDENCE_REGISTERED,
            description="Deterministic",
            actor_id="a1",
            evidence_sha256=sample_sha256,
            timestamp=ts,
            event_id="deterministic-id",
            metadata={"k": "v", "n": 1},
        )
        second = build_custody_event(
            evidence_id="EV-DET",
            action=CustodyAction.EVIDENCE_REGISTERED,
            description="Deterministic",
            actor_id="a1",
            evidence_sha256=sample_sha256,
            timestamp=ts,
            event_id="deterministic-id",
            metadata={"n": 1, "k": "v"},
        )
        assert first.event_hash == second.event_hash

    def test_unicode_metadata(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        event = custody_service.record_event(
            evidence_id="EV-UNI",
            action=CustodyAction.EVIDENCE_ANALYZED,
            description="Unicode note — 证据",
            evidence_sha256=sample_sha256,
            metadata={"note": "检验 üñíçødë 🔍"},
        )
        assert "证据" in event.description
        assert custody_service.verify_chain("EV-UNI").valid is True

    def test_provenance_preservation(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        event = custody_service.record_event(
            evidence_id="EV-PROV",
            action=CustodyAction.EVIDENCE_TRANSFERRED,
            description="Transferred to lab",
            actor_id="lead-9",
            actor_role="lead_investigator",
            source="api",
            source_ip="198.51.100.20",
            evidence_sha256=sample_sha256,
            evidence_path="/cases/EV-PROV/image.E01",
            original_filename="image.E01",
            file_size=4096,
            metadata={"destination": "lab-2"},
        )
        assert event.evidence_id == "EV-PROV"
        assert event.actor_id == "lead-9"
        assert event.source_ip == "198.51.100.20"
        assert event.evidence_sha256 == sample_sha256
        assert event.evidence_path.endswith("image.E01")
        assert event.metadata["destination"] == "lab-2"

    def test_no_django_dependency(self) -> None:
        custody_mod = importlib.import_module("app.services.custody_service")
        assert "django" not in getattr(custody_mod, "__dict__", {})
        source_path = Path(custody_mod.__file__).read_text(encoding="utf-8")
        assert "import django" not in source_path
        assert "from django" not in source_path
        # Engine must not require Django; if Django is somehow installed in the
        # environment, that still must not mean the service imports it.
        assert not hasattr(custody_mod, "django")

    def test_no_cookie_values(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        event = custody_service.record_event(
            evidence_id="EV-COOKIE",
            action=CustodyAction.EVIDENCE_ANALYZED,
            description="Browser analysis recorded",
            evidence_sha256=sample_sha256,
            metadata={"artifact": "browser_history"},
        )
        blob = event.model_dump_json()
        assert "cookie_value" not in blob.lower()

    def test_custody_service_orchestration(
        self, custody_service: CustodyService, sample_sha256: str
    ) -> None:
        built = custody_service.build_event(
            evidence_id="EV-ORCH",
            action=CustodyAction.EVIDENCE_ACQUIRED,
            description="built only",
            evidence_sha256=sample_sha256,
            link_to_latest=True,
        )
        assert built.previous_event_hash is None
        recorded = custody_service.record_event(
            evidence_id="EV-ORCH",
            action=CustodyAction.EVIDENCE_ACQUIRED,
            description="recorded",
            evidence_sha256=sample_sha256,
        )
        snapshot = custody_service.get_ledger_snapshot("EV-ORCH")
        assert snapshot.event_count == 1
        assert snapshot.latest_event_hash == recorded.event_hash
        exported = custody_service.export_for_timeline("EV-ORCH")
        assert exported[0]["source"] == "custody"
        assert custody_service.verify_chain("EV-ORCH").valid is True
