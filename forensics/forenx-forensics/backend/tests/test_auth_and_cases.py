"""Auth, JWT, and case access tests."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.conftest import auth_client

pytestmark = pytest.mark.django_db


def test_registration_and_jwt_login(api_client: APIClient, password: str) -> None:
    reg = api_client.post(
        "/api/auth/register/",
        {
            "username": "newbie",
            "email": "newbie@example.com",
            "password": password,
            "role": "investigator",
        },
        format="json",
    )
    assert reg.status_code == 201

    login = api_client.post(
        "/api/auth/login/",
        {"username": "newbie", "password": password},
        format="json",
    )
    assert login.status_code == 200
    assert "access" in login.data
    assert "refresh" in login.data

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    me = api_client.get("/api/auth/me/")
    assert me.status_code == 200
    assert me.data["username"] == "newbie"


def test_protected_case_endpoint_requires_auth(api_client: APIClient) -> None:
    resp = api_client.get("/api/cases/")
    assert resp.status_code == 401
    assert resp.data["success"] is False


def test_create_case(inv_client, investigator) -> None:
    resp = inv_client.post(
        "/api/cases/",
        {
            "title": "New Case",
            "description": "Created in test",
            "priority": "medium",
            "status": "open",
            "investigator": str(investigator.id),
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["title"] == "New Case"


def test_unauthorized_case_access(case, outsider) -> None:
    client = auth_client(outsider)
    resp = client.get(f"/api/cases/{case.id}/")
    assert resp.status_code == 403
