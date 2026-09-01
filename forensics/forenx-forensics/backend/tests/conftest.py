"""Shared fixtures for ForenX Django integration tests."""

from __future__ import annotations

import io

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserRole
from investigations.models import Case

User = get_user_model()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def password() -> str:
    return "TestPass123!"


def _make_user(username: str, role: str, password: str):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
        role=role,
    )


@pytest.fixture
def admin_user(password):
    return _make_user("admin1", UserRole.ADMINISTRATOR, password)


@pytest.fixture
def lead_user(password):
    return _make_user("lead1", UserRole.LEAD_INVESTIGATOR, password)


@pytest.fixture
def investigator(password):
    return _make_user("inv1", UserRole.INVESTIGATOR, password)


@pytest.fixture
def analyst(password):
    return _make_user("analyst1", UserRole.ANALYST, password)


@pytest.fixture
def auditor(password):
    return _make_user("auditor1", UserRole.AUDITOR, password)


@pytest.fixture
def outsider(password):
    return _make_user("outsider", UserRole.INVESTIGATOR, password)


def auth_client(user) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def inv_client(investigator) -> APIClient:
    return auth_client(investigator)


@pytest.fixture
def case(investigator, lead_user):
    c = Case.objects.create(
        title="Case Alpha",
        description="Integration test case",
        investigator=investigator,
        created_by=lead_user,
        priority="high",
        status="open",
    )
    c.members.add(investigator)
    return c


@pytest.fixture
def sample_upload():
    content = (
        b"confidential notes about bitcoin wallet transfer\n"
        b"benign grocery list milk bread\n"
    )
    return io.BytesIO(content)
