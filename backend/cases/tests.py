"""Ownership tests for the cases API (IDOR and investigator assignment)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from cases.models import Case

User = get_user_model()


class CaseOwnershipAPITests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username="user_a",
            email="a@example.com",
            password="Pass12345!",
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            email="b@example.com",
            password="Pass12345!",
        )
        self.case_a = Case.objects.create(
            title="Alpha case",
            description="Owned by A",
            investigator=self.user_a,
        )
        self.case_b = Case.objects.create(
            title="Bravo case",
            description="Owned by B",
            investigator=self.user_b,
        )

    def test_unauthenticated_list_returns_401(self):
        response = self.client.get("/api/cases/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_lists_only_own_cases(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get("/api/cases/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.case_a.id})

    def test_create_assigns_investigator_to_request_user(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/api/cases/",
            {"title": "New case", "description": "Created by A"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["investigator"], self.user_a.id)
        created = Case.objects.get(id=response.data["id"])
        self.assertEqual(created.investigator_id, self.user_a.id)

    def test_submitted_investigator_cannot_override_request_user(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/api/cases/",
            {
                "title": "Spoofed case",
                "description": "Should stay with A",
                "investigator": self.user_b.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["investigator"], self.user_a.id)
        created = Case.objects.get(id=response.data["id"])
        self.assertEqual(created.investigator_id, self.user_a.id)

    def test_user_b_cannot_retrieve_user_a_case(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get(f"/api/cases/{self.case_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_patch_user_a_case(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.patch(
            f"/api/cases/{self.case_a.id}/",
            {"title": "Hijacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.case_a.refresh_from_db()
        self.assertEqual(self.case_a.title, "Alpha case")

    def test_user_b_cannot_put_user_a_case(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.put(
            f"/api/cases/{self.case_a.id}/",
            {"title": "Hijacked", "description": "Taken"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.case_a.refresh_from_db()
        self.assertEqual(self.case_a.title, "Alpha case")

    def test_user_b_cannot_delete_user_a_case(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.delete(f"/api/cases/{self.case_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Case.objects.filter(id=self.case_a.id).exists())

    def test_user_a_can_retrieve_and_update_own_case(self):
        self.client.force_authenticate(user=self.user_a)
        retrieve = self.client.get(f"/api/cases/{self.case_a.id}/")
        self.assertEqual(retrieve.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve.data["id"], self.case_a.id)

        patch = self.client.patch(
            f"/api/cases/{self.case_a.id}/",
            {"title": "Updated by A"},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.case_a.refresh_from_db()
        self.assertEqual(self.case_a.title, "Updated by A")
        self.assertEqual(self.case_a.investigator_id, self.user_a.id)
