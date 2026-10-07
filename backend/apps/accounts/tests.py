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


from django.core import mail
from apps.accounts.models import EmailVerificationToken
from django.core.management import call_command
import io


class EmailVerificationAPITests(APITestCase):
    def test_registration_requires_verification_and_sends_email(self):
        mail.outbox.clear()
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "unverified_investigator",
                "email": "unverified@agency.gov",
                "password": "StrongPassword123!",
                "first_name": "Alex",
                "last_name": "Cross",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="unverified_investigator")
        self.assertFalse(user.is_email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify your ForenX account", mail.outbox[0].subject)

        # Attempt login before verification — must fail with clear message
        login_res = self.client.post(
            "/api/auth/login/",
            {
                "email": "unverified@agency.gov",
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Email address is not verified", str(login_res.data))

        # Verify email using generated token
        token_obj = EmailVerificationToken.objects.get(user=user, is_used=False)
        verify_res = self.client.post(
            "/api/auth/verify-email/",
            {"token": token_obj.token},
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.is_used)

        # Token cannot be reused (single-use)
        reuse_res = self.client.post(
            "/api/auth/verify-email/",
            {"token": token_obj.token},
            format="json",
        )
        self.assertEqual(reuse_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Login now succeeds after verification
        login_res_after = self.client.post(
            "/api/auth/login/",
            {
                "email": "unverified@agency.gov",
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res_after.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_res_after.data)

    def test_resend_verification_email(self):
        user = User.objects.create_user(
            username="resend_user",
            email="resend@agency.gov",
            password="StrongPassword123!",
            is_email_verified=False,
        )
        mail.outbox.clear()
        resend_res = self.client.post(
            "/api/auth/resend-verification/",
            {"email": "resend@agency.gov"},
            format="json",
        )
        self.assertEqual(resend_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        # If already verified, resend returns error
        user.is_email_verified = True
        user.save()
        resend_verified = self.client.post(
            "/api/auth/resend-verification/",
            {"email": "resend@agency.gov"},
            format="json",
        )
        self.assertEqual(resend_verified.status_code, status.HTTP_400_BAD_REQUEST)


class AdminUserManagementAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="main_admin",
            email="admin@forenx.io",
            password="AdminPass1234!",
            role="ADMIN",
            is_email_verified=True,
        )
        self.investigator = User.objects.create_user(
            username="investigator_mike",
            email="mike@forenx.io",
            password="InvestPass1234!",
            role="INVESTIGATOR",
            is_email_verified=True,
        )

    def test_investigator_cannot_access_admin_user_list(self):
        self.client.force_authenticate(user=self.investigator)
        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_users(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        usernames = [u["username"] for u in res.data]
        self.assertIn("main_admin", usernames)
        self.assertIn("investigator_mike", usernames)

    def test_admin_can_promote_investigator_to_admin(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f"/api/admin/users/{self.investigator.id}/",
            {"role": "ADMIN"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.investigator.refresh_from_db()
        self.assertEqual(self.investigator.role, "ADMIN")

    def test_admin_cannot_change_own_role(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f"/api/admin/users/{self.admin.id}/",
            {"role": "INVESTIGATOR"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, "ADMIN")

    def test_cannot_demote_last_admin(self):
        # Create second admin, then demote first
        admin2 = User.objects.create_user(
            username="admin2",
            email="admin2@forenx.io",
            password="Admin2Pass123!",
            role="ADMIN",
            is_email_verified=True,
        )
        self.client.force_authenticate(user=self.admin)
        # Demote admin2 works because self.admin is still active admin
        res = self.client.patch(
            f"/api/admin/users/{admin2.id}/",
            {"role": "INVESTIGATOR"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        admin2.refresh_from_db()
        self.assertEqual(admin2.role, "INVESTIGATOR")

        # Now only self.admin is left. Another admin cannot demote the last admin
        self.client.force_authenticate(user=admin2)
        # Even if admin2 attempts to demote self.admin, admin2 has role INVESTIGATOR -> 403
        res = self.client.patch(
            f"/api/admin/users/{self.admin.id}/",
            {"role": "INVESTIGATOR"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_deactivated_user_cannot_login(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f"/api/admin/users/{self.investigator.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.investigator.refresh_from_db()
        self.assertFalse(self.investigator.is_active)

        self.client.logout()
        login_res = self.client.post(
            "/api/auth/login/",
            {"email": "mike@forenx.io", "password": "InvestPass1234!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("deactivated", str(login_res.data).lower())

    def test_bootstrap_admin_management_command(self):
        out = io.StringIO()
        call_command(
            "bootstrap_admin",
            username="teacher_admin",
            email="teacher@school.edu",
            password="TeacherPass1234!",
            stdout=out,
        )
        teacher = User.objects.get(username="teacher_admin")
        self.assertEqual(teacher.role, "ADMIN")
        self.assertTrue(teacher.is_superuser)
        self.assertTrue(teacher.is_email_verified)
