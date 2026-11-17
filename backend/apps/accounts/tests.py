"""Authentication and registration tests."""

from unittest.mock import patch
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

    def test_rejection_of_duplicate_username(self):
        self.client.post(
            "/api/register/",
            {
                "username": "taken_username",
                "email": "user1@example.com",
                "password": "ValidPassword123!",
            },
            format="json",
        )
        response = self.client.post(
            "/api/register/",
            {
                "username": "taken_username",
                "email": "user2@example.com",
                "password": "ValidPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertIn("A user with that username already exists.", str(response.data["username"]))

    def test_common_available_username_succeeds(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "krishamange",
                "email": "krishamange_test@example.com",
                "password": "ValidPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="krishamange").exists())

    def test_rejection_of_password_too_similar_to_username(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "investigator_alice",
                "email": "alice@example.com",
                "password": "investigator_alice123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertIn("The password is too similar to the username.", str(response.data["password"]))

    def test_rejection_of_common_password(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "common_pwd_user",
                "email": "commonpwd@example.com",
                "password": "password",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertIn("This password is too common.", str(response.data["password"]))

    def test_rejection_of_entirely_numeric_password(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "numeric_pwd_user",
                "email": "numericpwd@example.com",
                "password": "1234567890",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertIn("This password is entirely numeric.", str(response.data["password"]))


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
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "john@forenx.io")
        self.assertEqual(response.data["user"]["username"], "investigator_john")
        self.assertEqual(response.data["user"]["role"], "INVESTIGATOR")

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
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "john@forenx.io")
        self.assertEqual(response.data["user"]["username"], "investigator_john")
        self.assertEqual(response.data["user"]["role"], "INVESTIGATOR")

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
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "john@forenx.io")
        self.assertEqual(response.data["user"]["username"], "investigator_john")
        self.assertEqual(response.data["user"]["role"], "INVESTIGATOR")

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
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "john@forenx.io")
        self.assertEqual(response.data["user"]["username"], "investigator_john")
        self.assertEqual(response.data["user"]["role"], "INVESTIGATOR")

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

    @patch("apps.accounts.serializers.send_verification_email", return_value=False)
    def test_registration_fails_and_rolls_back_when_email_sending_fails(self, mock_send):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "smtp_fail_user",
                "email": "smtpfail@agency.gov",
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("Unable to deliver verification email", str(response.data["email"]))
        self.assertFalse(User.objects.filter(username="smtp_fail_user").exists())

    @patch("apps.accounts.views.send_verification_email", return_value=False)
    def test_resend_verification_returns_500_when_email_sending_fails(self, mock_send):
        User.objects.create_user(
            username="resend_fail_user",
            email="resendfail@agency.gov",
            password="StrongPassword123!",
            is_email_verified=False,
        )
        response = self.client.post(
            "/api/auth/resend-verification/",
            {"email": "resendfail@agency.gov"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Failed to send verification email", str(response.data.get("error", "")))

    @patch("apps.accounts.serializers.create_verification_token", side_effect=RuntimeError("Token generation failed"))
    def test_registration_atomic_rollback_on_token_creation_failure(self, mock_token):
        with self.assertRaises(RuntimeError):
            self.client.post(
                "/api/auth/register/",
                {
                    "username": "atomic_token_fail_user",
                    "email": "tokenfail@agency.gov",
                    "password": "StrongPassword123!",
                },
                format="json",
            )
        self.assertFalse(User.objects.filter(username="atomic_token_fail_user").exists())

    @patch("apps.accounts.serializers.send_verification_email", return_value=False)
    @patch("django.contrib.auth.models.AbstractUser.delete", side_effect=Exception("Database lock error"))
    def test_registration_cleanup_failure_leaves_account_unverified_and_recoverable(self, mock_delete, mock_send):
        mail.outbox.clear()
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "cleanup_fail_user",
                "email": "cleanupfail@agency.gov",
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unable to deliver verification email", str(response.data.get("email", "")))

        # Account remains unverified and secure
        user = User.objects.get(username="cleanup_fail_user")
        self.assertFalse(user.is_email_verified)

        # Login is rejected
        login_res = self.client.post(
            "/api/auth/login/",
            {"email": "cleanupfail@agency.gov", "password": "StrongPassword123!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Recovers cleanly through resend verification
        resend_res = self.client.post(
            "/api/auth/resend-verification/",
            {"email": "cleanupfail@agency.gov"},
            format="json",
        )
        self.assertEqual(resend_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)


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
