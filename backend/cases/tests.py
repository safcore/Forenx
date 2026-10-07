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
        results = (
            response.data["results"]
            if isinstance(response.data, dict) and "results" in response.data
            else response.data
        )
        ids = {item["id"] for item in results}
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


class CaseFilterAndPaginationAPITests(APITestCase):
    def setUp(self):
        self.user_1 = User.objects.create_user(
            username="investigator_one",
            email="one@forenx.io",
            password="Pass12345!",
        )
        self.user_2 = User.objects.create_user(
            username="investigator_two",
            email="two@forenx.io",
            password="Pass12345!",
        )

        # Create user 1 cases in sequential order
        self.c1 = Case.objects.create(
            title="Laptop seizure at airport",
            description="Dell Latitude laptop retrieved from suspect luggage",
            priority="LOW",
            status="OPEN",
            investigator=self.user_1,
        )
        self.c2 = Case.objects.create(
            title="Malware forensic audit",
            description="Ransomware analysis on finance workstation",
            priority="HIGH",
            status="IN_PROGRESS",
            investigator=self.user_1,
        )
        self.c3 = Case.objects.create(
            title="Server intrusion malware triage",
            description="Database server breach investigation",
            priority="CRITICAL",
            status="OPEN",
            investigator=self.user_1,
        )
        self.c4 = Case.objects.create(
            title="Old mobile phone dump",
            description="Closed investigation of prepaid burner phone",
            priority="MEDIUM",
            status="CLOSED",
            investigator=self.user_1,
        )

        # User 2 case for testing ownership isolation
        self.u2_case = Case.objects.create(
            title="Confidential laptop espionage",
            description="High priority malware case for investigator 2",
            priority="HIGH",
            status="OPEN",
            investigator=self.user_2,
        )

    def test_newest_first_ordering(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get("/api/cases/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(returned_ids, [self.c4.id, self.c3.id, self.c2.id, self.c1.id])

    def test_pagination_default_structure(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get("/api/cases/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(len(response.data["results"]), 4)

    def test_pagination_custom_page_size_and_navigation(self):
        self.client.force_authenticate(user=self.user_1)
        # Request page 1 with page_size=2
        res_p1 = self.client.get("/api/cases/?page_size=2&page=1")
        self.assertEqual(res_p1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_p1.data["results"]), 2)
        self.assertIsNotNone(res_p1.data["next"])
        self.assertIsNone(res_p1.data["previous"])
        self.assertEqual(
            [item["id"] for item in res_p1.data["results"]],
            [self.c4.id, self.c3.id],
        )

        # Request page 2 with page_size=2
        res_p2 = self.client.get("/api/cases/?page_size=2&page=2")
        self.assertEqual(res_p2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_p2.data["results"]), 2)
        self.assertIsNone(res_p2.data["next"])
        self.assertIsNotNone(res_p2.data["previous"])
        self.assertEqual(
            [item["id"] for item in res_p2.data["results"]],
            [self.c2.id, self.c1.id],
        )

    def test_search_by_title(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get("/api/cases/?search=Malware")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.c2.id, self.c3.id})

    def test_search_by_description(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get("/api/cases/?search=Ransomware")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.c2.id})

    def test_status_filtering(self):
        self.client.force_authenticate(user=self.user_1)
        # Uppercase
        response = self.client.get("/api/cases/?status=OPEN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.c1.id, self.c3.id})

        # Case-insensitive
        response_lower = self.client.get("/api/cases/?status=open")
        self.assertEqual(response_lower.status_code, status.HTTP_200_OK)
        ids_lower = {item["id"] for item in response_lower.data["results"]}
        self.assertEqual(ids_lower, {self.c1.id, self.c3.id})

    def test_priority_filtering(self):
        self.client.force_authenticate(user=self.user_1)
        # Uppercase
        response = self.client.get("/api/cases/?priority=HIGH")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.c2.id})

        # Case-insensitive
        response_lower = self.client.get("/api/cases/?priority=high")
        self.assertEqual(response_lower.status_code, status.HTTP_200_OK)
        ids_lower = {item["id"] for item in response_lower.data["results"]}
        self.assertEqual(ids_lower, {self.c2.id})

    def test_combined_search_status_priority_and_pagination(self):
        self.client.force_authenticate(user=self.user_1)
        # Search "malware", status OPEN, priority CRITICAL
        response = self.client.get("/api/cases/?search=malware&status=OPEN&priority=CRITICAL")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.c3.id)

    def test_invalid_status_returns_400(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get("/api/cases/?status=NOT_VALID")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_invalid_priority_returns_400(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get("/api/cases/?priority=URGENT")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("priority", response.data)

    def test_search_with_ownership_isolation(self):
        self.client.force_authenticate(user=self.user_1)
        # user_2_case has "espionage" in title, user_1 has none
        response = self.client.get("/api/cases/?search=espionage")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_filtering_with_ownership_isolation(self):
        self.client.force_authenticate(user=self.user_1)
        # user_2 has an OPEN HIGH case, user_1 has NO case that is both OPEN and HIGH
        response = self.client.get("/api/cases/?status=OPEN&priority=HIGH")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_pagination_with_ownership_isolation(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.get("/api/cases/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Total count must only reflect user_1's 4 cases, not user_2's case
        self.assertEqual(response.data["count"], 4)
        for item in response.data["results"]:
            self.assertEqual(item["investigator"], self.user_1.id)


class CaseInvestigatorAndCloseAPITests(APITestCase):
    def setUp(self):
        self.investigator = User.objects.create_user(
            username="det_holmes",
            first_name="Sherlock",
            last_name="Holmes",
            email="holmes@agency.gov",
            password="SherlockPass123!",
            role="INVESTIGATOR",
        )
        self.other_user = User.objects.create_user(
            username="det_watson",
            email="watson@agency.gov",
            password="WatsonPass123!",
            role="INVESTIGATOR",
        )
        self.case = Case.objects.create(
            title="The Red-Headed League",
            description="Bank tunnel investigation",
            investigator=self.investigator,
            status="OPEN",
            priority="HIGH",
        )

    def test_case_detail_and_list_include_investigator_name(self):
        self.client.force_authenticate(user=self.investigator)
        res = self.client.get(f"/api/cases/{self.case.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["investigator_username"], "det_holmes")
        self.assertEqual(res.data["investigator_name"], "Sherlock Holmes")

        list_res = self.client.get("/api/cases/")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        first_case = list_res.data["results"][0]
        self.assertEqual(first_case["investigator_username"], "det_holmes")
        self.assertEqual(first_case["investigator_name"], "Sherlock Holmes")

    def test_close_case_endpoint_transitions_status(self):
        self.client.force_authenticate(user=self.investigator)
        close_res = self.client.post(f"/api/cases/{self.case.id}/close/")
        self.assertEqual(close_res.status_code, status.HTTP_200_OK)
        self.assertEqual(close_res.data["status"], "CLOSED")
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, "CLOSED")

    def test_other_user_cannot_close_case(self):
        self.client.force_authenticate(user=self.other_user)
        close_res = self.client.post(f"/api/cases/{self.case.id}/close/")
        self.assertEqual(close_res.status_code, status.HTTP_404_NOT_FOUND)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, "OPEN")
