"""Authentication and registration tests."""

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


class RegisterValidationAPITests(APITestCase):
    def test_successful_registration_with_valid_password(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "valid_user",
                "email": "valid_user@example.com",
                "password": "ComplexPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="valid_user").exists())

    def test_rejection_of_weak_password(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "weak_user",
                "email": "weak@example.com",
                "password": "123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.filter(username="weak_user").exists())

    def test_rejection_of_invalid_email(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "bad_email_user",
                "email": "not-a-valid-email",
                "password": "ValidPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_rejection_of_duplicate_email(self):
        # First registration
        self.client.post(
            "/api/register/",
            {
                "username": "first_user",
                "email": "duplicate@example.com",
                "password": "ValidPassword123!",
            },
            format="json",
        )
        # Second registration with case-variant of the same email
        response = self.client.post(
            "/api/register/",
            {
                "username": "second_user",
                "email": "DUPLICATE@example.com",
                "password": "ValidPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertFalse(User.objects.filter(username="second_user").exists())


class JWTLoginAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="investigator_john",
            email="john@forenx.io",
            password="StrongPass1234!",
            role="INVESTIGATOR",
        )

    def test_successful_login_with_username_and_password(self):
        response = self.client.post(
            "/api/token/",
            {
                "username": "investigator_john",
                "password": "StrongPass1234!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_successful_login_with_email_and_password(self):
        response = self.client.post(
            "/api/token/",
            {
                "email": "john@forenx.io",
                "password": "StrongPass1234!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_successful_login_with_email_in_username_field(self):
        response = self.client.post(
            "/api/token/",
            {
                "username": "john@forenx.io",
                "password": "StrongPass1234!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_successful_login_via_auth_login_endpoint(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "john@forenx.io",
                "password": "StrongPass1234!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_incorrect_password(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "john@forenx.io",
                "password": "IncorrectPassword!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def test_login_rejects_nonexistent_user(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "nonexistent@forenx.io",
                "password": "StrongPass1234!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_rejects_empty_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existing_jwt_refresh_behavior(self):
        login_res = self.client.post(
            "/api/auth/login/",
            {
                "email": "john@forenx.io",
                "password": "StrongPass1234!",
            },
            format="json",
        )
        refresh_token = login_res.data["refresh"]

        refresh_res = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

