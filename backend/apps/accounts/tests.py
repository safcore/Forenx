"""Public registration tests (role cannot be chosen by the client)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterRoleAPITests(APITestCase):
    def test_public_registration_succeeds_with_default_role(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "new_investigator",
                "email": "new@example.com",
                "password": "Pass12345!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="new_investigator")
        self.assertEqual(user.role, "INVESTIGATOR")
        self.assertEqual(response.data.get("role"), "INVESTIGATOR")

    def test_submitted_admin_role_is_ignored(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "would_be_admin",
                "email": "admin-attempt@example.com",
                "password": "Pass12345!",
                "role": "ADMIN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="would_be_admin")
        self.assertEqual(user.role, "INVESTIGATOR")
        self.assertEqual(response.data.get("role"), "INVESTIGATOR")

    def test_submitted_lead_role_is_ignored(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "would_be_lead",
                "email": "lead-attempt@example.com",
                "password": "Pass12345!",
                "role": "LEAD",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="would_be_lead")
        self.assertEqual(user.role, "INVESTIGATOR")
        self.assertEqual(response.data.get("role"), "INVESTIGATOR")
