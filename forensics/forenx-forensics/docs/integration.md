# Django Integration Guide

This document is for Member 1 (Django backend).

The ForenX forensics engine must remain an independent Python package. Django should **import** it, not fork it into the web project.

---

## Compatibility Rules

1. Do not import Django from inside this repository.
2. Do not move forensic algorithms into Django apps.
3. Treat service return values as immutable API contracts (Pydantic schemas).
4. Preserve evidence files as read-only from the engine’s point of view.
5. Call `setup_logging()` once during Django startup if ForenX logs are desired.

---

## Installation into the Backend Environment

From the Django project virtual environment:

```bash
pip install -e /path/to/forenx-forensics
# or relative path
pip install -e ../forenx-forensics
```

Confirm imports:

```python
from app.services.hash_service import HashService
from app.services.metadata_service import MetadataService
from app.services.keyword_service import KeywordSearchService
from app.services.browser_service import BrowserService
from app.services.timeline_service import TimelineService
from app.services.custody_service import CustodyService
from app.services.report_service import ReportService
from app.services.ai_service import AIService
```

---

## Recommended Django Startup Hook

```python
# forensics_app/apps.py
from django.apps import AppConfig


class ForensicsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "forensics_app"

    def ready(self) -> None:
        from app.utils.logger import setup_logging

        setup_logging()
```

---

## Sample Django Service Wrapper

Keep thin wrappers in Django so views/serializers never call feature packages directly.

```python
# forensics_app/services/forenx_bridge.py
"""Thin Django-facing wrappers around the ForenX engine."""

from __future__ import annotations

from pathlib import Path

from app.schemas.ai import AIAnalysis
from app.schemas.browser import BrowserResult
from app.schemas.hash import HashResult, HashVerificationResult, IntegrityResult
from app.schemas.keyword import KeywordResult, SearchResult
from app.schemas.metadata import MetadataResult
from app.schemas.timeline import TimelineResult
from app.services.ai_service import AIService
from app.services.browser_service import BrowserService
from app.services.hash_service import HashService
from app.services.keyword_service import KeywordSearchService
from app.services.metadata_service import MetadataService
from app.services.timeline_service import TimelineService


class ForenXBridge:
    """Adapter used by Django views / Celery tasks."""

    def __init__(self) -> None:
        self.hashes = HashService()
        self.metadata = MetadataService(hash_service=self.hashes)
        self.keywords = KeywordSearchService()
        self.browser = BrowserService()
        self.timeline = TimelineService(
            browser_service=self.browser,
            metadata_service=self.metadata,
        )
        self.ai = AIService()  # disabled by default; enable deliberately in Django settings

    def hash_evidence(self, path: str | Path) -> list[HashResult]:
        return self.hashes.calculate_hashes(path)

    def verify_evidence(
        self,
        path: str | Path,
        expected_hash: str,
        algorithm: str = "sha256",
    ) -> HashVerificationResult:
        return self.hashes.verify(path, expected_hash, algorithm)

    def integrity_check(
        self,
        path: str | Path,
        original_hash: str,
        algorithm: str = "sha256",
    ) -> IntegrityResult:
        return self.hashes.integrity_check(path, original_hash, algorithm)

    def extract_metadata(self, path: str | Path) -> MetadataResult:
        return self.metadata.extract(path)

    def search_keywords(
        self,
        path: str | Path,
        keyword: str,
    ) -> KeywordResult:
        return self.keywords.search(path, keyword)

    def search_case_folder(
        self,
        directory: str | Path,
        keywords: list[str],
    ) -> SearchResult:
        return self.keywords.search_directory(directory, keywords)

    def analyze_browser_profile(self, profile_dir: str | Path) -> BrowserResult:
        return self.browser.analyze_browser(profile_dir)

    def reconstruct_timeline(self, path: str | Path) -> TimelineResult:
        return self.timeline.build_timeline(path)

    def assistive_analysis(self, **kwargs) -> AIAnalysis:
        """Optional advisory analysis over already-computed forensic results."""
        return self.ai.analyze(**kwargs)
```

Example API view usage:

```python
from rest_framework.response import Response
from rest_framework.views import APIView

from forensics_app.services.forenx_bridge import ForenXBridge


class HashEvidenceView(APIView):
    def post(self, request):
        bridge = ForenXBridge()
        path = request.data["file_path"]
        results = bridge.hash_evidence(path)
        return Response([item.model_dump(mode="json") for item in results])
```

---

## Mapping Engine Results to Django Models

Suggested pattern:

1. Persist evidence file path + case ID in Django models.
2. Call ForenX service.
3. Serialize schema with `model_dump(mode="json")`.
4. Store selected fields in Django tables or JSONField snapshots.

Do not reimplement hash / metadata / keyword / browser / timeline logic in serializers.

---

## Error Handling Suggestion

Catch `app.utils.exceptions.ForenXError` in the Django layer and map to HTTP responses:

| Engine exception family | Suggested HTTP mapping |
|-------------------------|------------------------|
| `EvidenceFileError` | 404 / 400 |
| `UnsupportedFileTypeError` | 400 |
| `UnsupportedAlgorithmError` | 400 |
| `InvalidHashError` | 400 |
| `KeywordSearchError` | 400 / 422 |
| `BrowserHistoryError` | 422 |
| `MetadataExtractionError` | 422 |
| `AIAnalysisError` | 400 / 422 |
| Other `ForenXError` | 500 |

---

## Independence Checklist

- [ ] Engine installed as package dependency
- [ ] No Django imports inside `forenx-forensics`
- [ ] Views call bridge/services only
- [ ] Evidence originals never written by engine adapters
- [ ] Tests for wrappers mock services or use sample evidence paths
- [ ] AI output presented as advisory (never as independent forensic evidence)

See also: [ai-integration.md](ai-integration.md)

---

## Phase 10 Django Host

A concrete Django/DRF adapter now ships under `backend/`.

- Engine remains Django-free (`app/` has zero Django imports)
- JWT auth, roles, models, and API routes live only in `backend/`
- Thin wrappers call existing ForenX services — no duplicated forensic algorithms

Primary references:

- [django-integration.md](django-integration.md)
- [backend/README.md](../backend/README.md)
